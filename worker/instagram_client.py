"""Instagram Graph API: publishing to Stories and refreshing long-lived tokens.

Mirrors the OAuth logic in src/lib/instagram.ts on the Next.js side — keep
both in sync if the Graph API version or flow changes.
"""

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any

import requests

logger = logging.getLogger(__name__)

GRAPH_API_VERSION = "v21.0"
GRAPH_BASE = f"https://graph.facebook.com/{GRAPH_API_VERSION}"

# Refresh proactively well before the ~60-day expiry so a missed run or two
# doesn't leave a tenant stranded needing a manual browser re-login.
REFRESH_IF_EXPIRING_WITHIN = timedelta(days=15)


class InstagramApiError(RuntimeError):
    pass


def _get(path: str, params: dict[str, str]) -> dict[str, Any]:
    response = requests.get(f"{GRAPH_BASE}{path}", params=params, timeout=20)
    payload = response.json()
    if not response.ok:
        raise InstagramApiError(payload.get("error", {}).get("message", response.text))
    return payload


def _post(path: str, params: dict[str, str]) -> dict[str, Any]:
    response = requests.post(f"{GRAPH_BASE}{path}", data=params, timeout=20)
    payload = response.json()
    if not response.ok:
        raise InstagramApiError(payload.get("error", {}).get("message", response.text))
    return payload


def publish_story(ig_business_account_id: str, page_access_token: str, image_url: str) -> str:
    """Publishes a single image to Stories. Returns the published media id."""
    created = _post(
        f"/{ig_business_account_id}/media",
        {
            "image_url": image_url,
            "media_type": "STORIES",
            "access_token": page_access_token,
        },
    )
    creation_id = created["id"]

    published = _post(
        f"/{ig_business_account_id}/media_publish",
        {"creation_id": creation_id, "access_token": page_access_token},
    )
    return published["id"]


def needs_refresh(token_expires_at: str | None) -> bool:
    if not token_expires_at:
        return True
    expires = datetime.fromisoformat(token_expires_at.replace("Z", "+00:00"))
    return expires - datetime.now(timezone.utc) < REFRESH_IF_EXPIRING_WITHIN


def refresh_tokens(long_lived_user_token: str, ig_business_account_id: str) -> dict[str, Any]:
    """Exchanges the stored user token for a fresh 60-day one and re-derives
    the Page access token for the same IG business account.

    Returns a dict with new_user_token, new_page_token and new_expires_at, or
    raises InstagramApiError if the refresh fails (most commonly because the
    user revoked access or the token already fully expired — in that case
    the tenant needs to reconnect Instagram manually from the dashboard).
    """
    app_id = os.environ["FACEBOOK_APP_ID"]
    app_secret = os.environ["FACEBOOK_APP_SECRET"]

    exchanged = _get(
        "/oauth/access_token",
        {
            "grant_type": "fb_exchange_token",
            "client_id": app_id,
            "client_secret": app_secret,
            "fb_exchange_token": long_lived_user_token,
        },
    )
    new_user_token = exchanged["access_token"]

    pages = _get(
        "/me/accounts",
        {"access_token": new_user_token, "fields": "id,access_token,instagram_business_account"},
    )["data"]

    matching_page = next(
        (
            p
            for p in pages
            if p.get("instagram_business_account", {}).get("id") == ig_business_account_id
        ),
        None,
    )
    if not matching_page:
        raise InstagramApiError(
            "Could not find the Page linked to this Instagram account after refresh "
            "— the user may have unlinked or revoked access."
        )

    return {
        "new_user_token": new_user_token,
        "new_page_token": matching_page["access_token"],
        "new_expires_at": (datetime.now(timezone.utc) + timedelta(days=60)).isoformat(),
    }
