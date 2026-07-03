"""Client for the Shopee Affiliate Open API (GraphQL).

IMPORTANT: this is based on the public documentation mirror at
https://www.affiliateshopee.com.br/documentacao (Shopee does not appear to
publish this reference on a shopee.com.br domain in an easily crawlable
form). Treat the query/field names below as a best-effort starting point,
not a guaranteed-correct contract — cross-check against whatever docs/
Playground your own Shopee affiliate dashboard exposes once your API access
is approved, and adjust `PRODUCT_OFFER_QUERY` if fields have changed.
"""

import hashlib
import json
import time
from typing import Any

import requests

GRAPHQL_ENDPOINT = "https://open-api.affiliate.shopee.com.br/graphql"

PRODUCT_OFFER_QUERY = """
{{
  productOfferV2(keyword: "{keyword}", listType: 1, sortType: 5, page: {page}, limit: {limit}) {{
    nodes {{
      itemId
      productName
      priceMin
      priceMax
      imageUrl
      offerLink
      commissionRate
      shopName
    }}
    pageInfo {{
      page
      limit
      hasNextPage
    }}
  }}
}}
""".strip()


class ShopeeApiError(RuntimeError):
    pass


def _build_signature(app_id: str, timestamp: int, payload: str, app_secret: str) -> str:
    raw = f"{app_id}{timestamp}{payload}{app_secret}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _post(app_id: str, app_secret: str, query: str) -> dict[str, Any]:
    body = json.dumps({"query": query})
    timestamp = int(time.time())
    signature = _build_signature(app_id, timestamp, body, app_secret)

    headers = {
        "Content-Type": "application/json",
        "Authorization": (
            f"SHA256 Credential={app_id}, Timestamp={timestamp}, Signature={signature}"
        ),
    }

    response = requests.post(GRAPHQL_ENDPOINT, data=body, headers=headers, timeout=20)
    response.raise_for_status()
    payload = response.json()

    if "errors" in payload and payload["errors"]:
        raise ShopeeApiError(str(payload["errors"]))

    return payload["data"]


def fetch_products_from_api(
    app_id: str, app_secret: str, keyword: str = "", page: int = 1, limit: int = 20
) -> list[dict[str, Any]]:
    """Returns a normalized list of product dicts, or raises ShopeeApiError."""
    query = PRODUCT_OFFER_QUERY.format(keyword=keyword, page=page, limit=limit)
    data = _post(app_id, app_secret, query)
    nodes = data.get("productOfferV2", {}).get("nodes", [])

    return [
        {
            "id": str(node["itemId"]),
            "name": node["productName"],
            "price": node.get("priceMin"),
            "image_url": node["imageUrl"],
            "affiliate_link": node["offerLink"],
            "shop_name": node.get("shopName"),
        }
        for node in nodes
    ]
