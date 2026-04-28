"""WooCommerce REST API + WordPress REST API wrapper.

Utilise pour :
- Lire/maj commandes (status, meta, notes)
- Lire/maj produits (stock, prix)
- Publier articles blog (WP REST + media)
"""
import base64
import logging
import time
from typing import Optional

import requests

logger = logging.getLogger("automation.clients.wc")


class WooClient:
    """Client unifie WooCommerce REST + WordPress REST.

    WC auth : Consumer Key / Consumer Secret (HTTP Basic).
    WP auth : Application Password (HTTP Basic) — uniquement si WP_USER fourni.
    """

    def __init__(
        self,
        base_url: str,
        wc_key: str,
        wc_secret: str,
        wp_user: str = "",
        wp_app_password: str = "",
    ):
        self.base_url = base_url.rstrip("/")
        self.wc_session = requests.Session()
        self.wc_session.auth = (wc_key, wc_secret)
        self._rate_limit = 0.3

        # Session distincte pour WP REST (Application Password)
        self.wp_session = requests.Session()
        if wp_user and wp_app_password:
            token = base64.b64encode(
                f"{wp_user}:{wp_app_password}".encode("utf-8")
            ).decode("ascii")
            self.wp_session.headers["Authorization"] = f"Basic {token}"

    # ------------------------------------------------------------ HTTP CORE
    def _request(
        self,
        method: str,
        endpoint: str,
        retries: int = 3,
        api: str = "wc",
        **kwargs,
    ) -> dict:
        if api == "wc":
            url = f"{self.base_url}/wp-json/wc/v3/{endpoint.lstrip('/')}"
            session = self.wc_session
        elif api == "wp":
            url = f"{self.base_url}/wp-json/wp/v2/{endpoint.lstrip('/')}"
            session = self.wp_session
        else:
            url = f"{self.base_url}{endpoint}"
            session = self.wc_session

        last_error = None
        for attempt in range(retries):
            try:
                resp = session.request(method, url, timeout=30, **kwargs)
                resp.raise_for_status()
                time.sleep(self._rate_limit)
                if resp.content:
                    return resp.json()
                return {}
            except requests.RequestException as e:
                last_error = e
                logger.warning(
                    "WC %s %s attempt %d failed: %s",
                    method,
                    endpoint,
                    attempt + 1,
                    e,
                )
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)
        logger.error("WC %s %s failed after %d attempts", method, endpoint, retries)
        raise last_error

    def _get_paginated(self, endpoint: str, per_page: int = 100, **params) -> list:
        all_items = []
        page = 1
        params["per_page"] = per_page
        while True:
            params["page"] = page
            items = self._request("GET", endpoint, params=params)
            if not items:
                break
            all_items.extend(items)
            if len(items) < per_page:
                break
            page += 1
        return all_items

    # ----------------------------------------------------------------- ORDERS
    def get_orders(
        self,
        status: str = None,
        after: str = None,
        before: str = None,
        per_page: int = 50,
    ) -> list:
        params = {}
        if status:
            params["status"] = status
        if after:
            params["after"] = after
        if before:
            params["before"] = before
        return self._get_paginated("orders", per_page=per_page, **params)

    def get_order(self, order_id: int) -> dict:
        return self._request("GET", f"orders/{order_id}")

    def update_order(self, order_id: int, data: dict) -> dict:
        return self._request("PUT", f"orders/{order_id}", json=data)

    def update_order_meta(self, order_id: int, key: str, value: str) -> dict:
        return self.update_order(
            order_id, {"meta_data": [{"key": key, "value": value}]}
        )

    def add_order_note(
        self, order_id: int, note: str, customer_note: bool = False
    ) -> dict:
        return self._request(
            "POST",
            f"orders/{order_id}/notes",
            json={"note": note, "customer_note": customer_note},
        )

    # --------------------------------------------------------------- PRODUCTS
    def get_products(
        self,
        status: str = "any",
        per_page: int = 100,
        sku: str = None,
        category: str = None,
    ) -> list:
        params = {"status": status}
        if sku:
            params["sku"] = sku
        if category:
            params["category"] = category
        return self._get_paginated("products", per_page=per_page, **params)

    def get_product(self, product_id: int) -> Optional[dict]:
        try:
            return self._request("GET", f"products/{product_id}")
        except Exception as e:
            logger.warning("get_product(%d) failed: %s", product_id, e)
            return None

    def get_product_by_sku(self, sku: str) -> Optional[dict]:
        try:
            results = self._request(
                "GET", "products", params={"sku": sku, "per_page": 1}
            )
            if results:
                return results[0]
        except Exception as e:
            logger.warning("get_product_by_sku(%s) failed: %s", sku, e)
        return None

    def update_product(self, product_id: int, data: dict) -> dict:
        return self._request("PUT", f"products/{product_id}", json=data)

    def create_product(self, data: dict) -> dict:
        return self._request("POST", "products", json=data)

    def batch_update_products(
        self, updates: list, batch_size: int = 10, delay: float = 2.0
    ) -> list:
        """Bulk update via /products/batch."""
        results = []
        for i in range(0, len(updates), batch_size):
            batch = updates[i:i + batch_size]
            r = self._request("POST", "products/batch", json={"update": batch})
            results.append(r)
            logger.info("Batch %d: %d products updated", i // batch_size + 1, len(batch))
            if i + batch_size < len(updates):
                time.sleep(delay)
        return results

    # ------------------------------------------------------------- CATEGORIES
    def get_categories(self, per_page: int = 100) -> dict:
        cats = self._get_paginated("products/categories", per_page=per_page)
        return {c["slug"]: c["id"] for c in cats}

    # ------------------------------------------------------- WP : POSTS / MEDIA
    def upload_media(self, image_bytes: bytes, filename: str, mime: str = "image/jpeg") -> dict:
        """Upload image dans la mediatheque WP (WP REST)."""
        url = f"{self.base_url}/wp-json/wp/v2/media"
        headers = {
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Type": mime,
        }
        r = self.wp_session.post(url, headers=headers, data=image_bytes, timeout=60)
        r.raise_for_status()
        return r.json()

    def create_post(
        self,
        title: str,
        content: str,
        excerpt: str = "",
        status: str = "publish",
        categories: list = None,
        tags: list = None,
        featured_media: int = None,
        slug: str = None,
        meta: dict = None,
    ) -> dict:
        """Cree un article de blog WP."""
        payload = {
            "title": title,
            "content": content,
            "excerpt": excerpt,
            "status": status,
        }
        if categories:
            payload["categories"] = categories
        if tags:
            payload["tags"] = tags
        if featured_media:
            payload["featured_media"] = featured_media
        if slug:
            payload["slug"] = slug
        if meta:
            payload["meta"] = meta
        return self._request("POST", "posts", api="wp", json=payload)
