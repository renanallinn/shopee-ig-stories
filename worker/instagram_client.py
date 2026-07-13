"""Instagram Graph API: publishing to Stories and refreshing long-lived tokens.

Uses "Instagram API with Instagram Login" (Business Login) — no Facebook Page
involved. A single Instagram User access token is used for everything
(refresh and publish), against graph.instagram.com.

Mirrors the OAuth logic in src/lib/instagram.ts on the Next.js side — keep
both in sync if the Graph API version or flow changes.
"""

import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Any

import requests

logger = logging.getLogger(__name__)

GRAPH_API_VERSION = "v21.0"
GRAPH_BASE = f"https://graph.instagram.com/{GRAPH_API_VERSION}"

# Instagram processes the uploaded image asynchronously — publishing before
# the container reaches FINISHED fails with "Media ID is not available".
CONTAINER_POLL_INTERVAL_SECONDS = 3
CONTAINER_POLL_TIMEOUT_SECONDS = 60

# Refresh proactively well before the ~60-day expiry so a missed run or two
# doesn't leave a tenant stranded needing a manual browser re-login. Tokens
# must also be at least 24h old to be refreshable, which our hourly/refresh
# cadence comfortably satisfies.
REFRESH_IF_EXPIRING_WITHIN = timedelta(days=15)


class InstagramApiError(RuntimeError):
    pass


def _get(url: str, params: dict[str, str]) -> dict[str, Any]:
    response = requests.get(url, params=params, timeout=20)
    payload = response.json()
    if not response.ok:
        raise InstagramApiError(
            payload.get("error_message") or payload.get("error", {}).get("message", response.text)
        )
    return payload


def _post(url: str, params: dict[str, str]) -> dict[str, Any]:
    response = requests.post(url, data=params, timeout=20)
    payload = response.json()
    if not response.ok:
        raise InstagramApiError(
            payload.get("error_message") or payload.get("error", {}).get("message", response.text)
        )
    return payload


def _wait_until_container_ready(creation_id: str, access_token: str) -> None:
    deadline = time.monotonic() + CONTAINER_POLL_TIMEOUT_SECONDS
    while True:
        status = _get(
            f"{GRAPH_BASE}/{creation_id}",
            {"fields": "status_code", "access_token": access_token},
        )["status_code"]
        if status == "FINISHED":
            return
        if status == "ERROR":
            raise InstagramApiError(f"Media container {creation_id} failed processing (status ERROR)")
        if time.monotonic() >= deadline:
            raise InstagramApiError(
                f"Media container {creation_id} did not finish processing within "
                f"{CONTAINER_POLL_TIMEOUT_SECONDS}s (last status: {status})"
            )
        logger.info("Container %s not ready yet (status=%s), waiting...", creation_id, status)
        time.sleep(CONTAINER_POLL_INTERVAL_SECONDS)


def publish_story(ig_business_account_id: str, access_token: str, image_url: str) -> str:
    """Publishes a single image to Stories. Returns the published media id."""
    created = _post(
        f"{GRAPH_BASE}/{ig_business_account_id}/media",
        {
            "image_url": image_url,
            "media_type": "STORIES",
            "access_token": access_token,
        },
    )
    creation_id = created["id"]

    _wait_until_container_ready(creation_id, access_token)

    published = _post(
        f"{GRAPH_BASE}/{ig_business_account_id}/media_publish",
        {"creation_id": creation_id, "access_token": access_token},
    )
    return published["id"]


def needs_refresh(token_expires_at: str | None) -> bool:
    if not token_expires_at:
        return True
    expires = datetime.fromisoformat(token_expires_at.replace("Z", "+00:00"))
    return expires - datetime.now(timezone.utc) < REFRESH_IF_EXPIRING_WITHIN


def refresh_token(long_lived_access_token: str) -> dict[str, Any]:
    """Refreshes the Instagram long-lived access token for another 60 days.

    Raises InstagramApiError if the refresh fails (most commonly because the
    token is less than 24h old, already expired, or access was revoked — in
    the latter cases the tenant needs to reconnect Instagram manually from
    the dashboard).
    """
    data = _get(
        "https://graph.instagram.com/refresh_access_token",
        {"grant_type": "ig_refresh_token", "access_token": long_lived_access_token},
    )
    return {
        "new_access_token": data["access_token"],
        "new_expires_at": (
            datetime.now(timezone.utc) + timedelta(seconds=data["expires_in"])
        ).isoformat(),
    }
