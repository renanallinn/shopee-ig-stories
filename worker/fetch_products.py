"""Resolves the list of products to draw from for a single tenant.

Priority: Shopee Affiliate Open API (if app_id/secret are configured and the
call succeeds) -> manual_products fallback list saved on the dashboard.
Raises if neither source yields anything, so the caller can skip the tenant.
"""

import logging
from typing import Any

from crypto_util import decrypt_secret
from shopee_client import ShopeeApiError, fetch_products_from_api

logger = logging.getLogger(__name__)


class NoProductsAvailable(RuntimeError):
    pass


def get_products_for_tenant(connection: dict[str, Any]) -> list[dict[str, Any]]:
    app_id = connection.get("shopee_app_id")
    app_secret_encrypted = connection.get("shopee_app_secret_encrypted")

    if app_id and app_secret_encrypted:
        try:
            app_secret = decrypt_secret(app_secret_encrypted)
            products = fetch_products_from_api(app_id, app_secret)
            if products:
                return products
            logger.warning(
                "Shopee API returned no products for user %s, falling back to manual list",
                connection.get("user_id"),
            )
        except ShopeeApiError:
            logger.exception(
                "Shopee API call failed for user %s, falling back to manual list",
                connection.get("user_id"),
            )

    manual_products = connection.get("manual_products") or []
    if manual_products:
        return manual_products

    raise NoProductsAvailable(
        f"No Shopee API access and no manual product list for user {connection.get('user_id')}"
    )
