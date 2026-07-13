"""Multi-tenant pipeline, split into two passes because Instagram must fetch
the story image from a public URL — the image has to already be pushed to
GitHub before we can tell Instagram to publish it.

Pass 1 (`generate`): for every active tenant, pick their next product and
render the story image into generated/<user_id>/<file>.jpg. Run by the
workflow, followed by a `git add generated && git commit && git push`.

Pass 2 (`publish`): reads the manifest pass 1 wrote, refreshes Instagram
tokens if they're close to expiring, and publishes each image via the Graph
API using the now-public raw.githubusercontent.com URL. Updates
posting_state/posts_log per tenant so the next run doesn't repeat products.

Secrets are never written to the manifest — only user_id and public,
non-sensitive fields — because generated/ and the manifest sit in the same
git-tracked worker directory.
"""

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from crypto_util import decrypt_secret, encrypt_secret
from fetch_products import NoProductsAvailable, get_products_for_tenant
from instagram_client import InstagramApiError, needs_refresh, publish_story, refresh_token
from story_image import generate_story_image
from supabase_client import get_service_client

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("orchestrator")

WORKER_DIR = Path(__file__).parent
GENERATED_DIR = WORKER_DIR / "generated"
MANIFEST_PATH = WORKER_DIR / "manifest.json"


def _public_image_url(relative_path: str) -> str:
    repo = os.environ["GITHUB_REPOSITORY"]  # set automatically in GitHub Actions
    branch = os.environ.get("GITHUB_REF_NAME", "main")
    return f"https://raw.githubusercontent.com/{repo}/{branch}/worker/generated/{relative_path}"


def run_generate(dry_run: bool) -> None:
    supabase = get_service_client()
    connections = (
        supabase.table("store_connections")
        .select("*")
        .eq("is_active", True)
        .not_.is_("ig_business_account_id", "null")
        .execute()
        .data
    )

    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    manifest: list[dict] = []

    for connection in connections:
        user_id = connection["user_id"]
        try:
            products = get_products_for_tenant(connection)

            # .maybe_single() should return data=None for a first-time user
            # with no posting_state row yet, but postgrest can respond 406
            # for the zero-row case, which some client versions surface as
            # execute() returning None outright rather than data=None.
            try:
                state_res = (
                    supabase.table("posting_state")
                    .select("last_product_index")
                    .eq("user_id", user_id)
                    .maybe_single()
                    .execute()
                )
                state_data = state_res.data if state_res else None
            except Exception:
                state_data = None
            current_index = (state_data or {}).get("last_product_index", 0)
            product = products[current_index % len(products)]
            new_index = current_index + 1

            timestamp = int(time.time())
            relative_path = f"{user_id}/{timestamp}.jpg"
            output_path = GENERATED_DIR / user_id
            output_path.mkdir(parents=True, exist_ok=True)
            generate_story_image(product, str(GENERATED_DIR / relative_path))

            manifest.append(
                {
                    "user_id": user_id,
                    "product_id": str(product.get("id")),
                    "product_name": product.get("name"),
                    "image_relative_path": relative_path,
                    "image_public_url": _public_image_url(relative_path),
                    "new_index": new_index,
                }
            )
            logger.info("Generated story for user %s: %s", user_id, product.get("name"))
        except NoProductsAvailable as exc:
            logger.warning("Skipping user %s: %s", user_id, exc)
        except Exception:
            logger.exception("Failed to generate story for user %s", user_id)

    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2))
    logger.info(
        "%s %d stories to generated/ (manifest at %s)",
        "Would have generated" if dry_run else "Generated",
        len(manifest),
        MANIFEST_PATH,
    )


def run_publish(dry_run: bool) -> None:
    if not MANIFEST_PATH.exists():
        logger.info("No manifest found, nothing to publish.")
        return

    manifest = json.loads(MANIFEST_PATH.read_text())
    supabase = get_service_client()

    for entry in manifest:
        user_id = entry["user_id"]
        try:
            connection = (
                supabase.table("store_connections")
                .select("*")
                .eq("user_id", user_id)
                .single()
                .execute()
                .data
            )

            access_token_encrypted = connection["ig_access_token_encrypted"]
            ig_business_account_id = connection["ig_business_account_id"]

            if needs_refresh(connection.get("ig_token_expires_at")):
                logger.info("Refreshing Instagram token for user %s", user_id)
                refreshed = refresh_token(decrypt_secret(access_token_encrypted))
                access_token_encrypted = encrypt_secret(refreshed["new_access_token"])
                if not dry_run:
                    supabase.table("store_connections").update(
                        {
                            "ig_access_token_encrypted": access_token_encrypted,
                            "ig_token_expires_at": refreshed["new_expires_at"],
                        }
                    ).eq("user_id", user_id).execute()

            if dry_run:
                logger.info(
                    "[dry-run] Would publish '%s' for user %s using %s",
                    entry["product_name"],
                    user_id,
                    entry["image_public_url"],
                )
                continue

            media_id = publish_story(
                ig_business_account_id,
                decrypt_secret(access_token_encrypted),
                entry["image_public_url"],
            )

            supabase.table("posting_state").upsert(
                {
                    "user_id": user_id,
                    "last_product_id": entry["product_id"],
                    "last_product_index": entry["new_index"],
                    "last_posted_at": datetime.now(timezone.utc).isoformat(),
                },
                on_conflict="user_id",
            ).execute()

            supabase.table("posts_log").insert(
                {
                    "user_id": user_id,
                    "product_id": entry["product_id"],
                    "product_name": entry["product_name"],
                    "ig_media_id": media_id,
                    "status": "success",
                }
            ).execute()

            logger.info("Published story for user %s (media %s)", user_id, media_id)
        except InstagramApiError as exc:
            logger.exception("Instagram API error for user %s", user_id)
            if not dry_run:
                supabase.table("posts_log").insert(
                    {
                        "user_id": user_id,
                        "product_id": entry.get("product_id"),
                        "product_name": entry.get("product_name"),
                        "status": "error",
                        "error_message": str(exc),
                    }
                ).execute()
        except Exception:
            logger.exception("Unexpected error publishing for user %s", user_id)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["generate", "publish"])
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.mode == "generate":
        run_generate(args.dry_run)
    else:
        run_publish(args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
