"""CJ Dropshipping API client.

Documentation officielle : https://developers.cjdropshipping.com/

Auth : POST /api/authentication/getAccessToken avec apiKey
       (pas email/password — utiliser uniquement la cle au format
        "CJxxxxxxx@api@xxxxxxxxxxxxxxxxxxxxxxxxx")

Le token a une duree de vie ~14 jours, refresh automatique via re-auth.
Rate limit : ~1 req/s, on respecte 1.2s entre requetes.
"""
import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

import requests

logger = logging.getLogger("automation.clients.cj")

# CJ envoie les tokens vers cette base
DEFAULT_BASE = "https://developers.cjdropshipping.com"


class CJClient:
    """Client minimal pour les besoins Gavio :
    - get_product_stock(vid)            -> stock dispo en entrepot
    - get_product_detail(pid)           -> infos produit
    - create_order(payload)             -> creer une commande dropshipping
    - get_order_detail(cj_order_id)     -> tracking + status
    - get_tracking(cj_order_id)         -> numero de suivi + transporteur
    - list_new_products(category, ...)  -> nouveautes catalogue
    """

    def __init__(self, api_key: str, base_url: str = DEFAULT_BASE):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self._token: Optional[str] = None
        self._token_expiry: Optional[datetime] = None
        self._last_call_at = 0.0
        self._min_interval = 1.2  # secondes

    # ------------------------------------------------------------------ AUTH
    def _ensure_token(self) -> str:
        """Recupere/refresh le token CJ."""
        if (
            self._token
            and self._token_expiry
            and datetime.now(tz=timezone.utc) < self._token_expiry - timedelta(hours=1)
        ):
            return self._token

        url = f"{self.base_url}/api2.0/v1/authentication/getAccessToken"
        # CJ accepte l'auth "apiKey only" : format CJxxx@api@xxxx
        # certains comptes utilisent email/password — ici on utilise la cle complete
        payload = {"email": "", "apiKey": self.api_key}

        # Format alternatif pour certaines integrations : extraire email depuis cle
        if "@api@" in self.api_key:
            email_part, _, key_part = self.api_key.partition("@api@")
            payload = {"email": f"{email_part}@api", "password": key_part}

        try:
            r = self.session.post(url, json=payload, timeout=20)
            r.raise_for_status()
            data = r.json()
            if data.get("result") and data.get("data"):
                self._token = data["data"]["accessToken"]
                # CJ ne renvoie pas toujours d'expiry — fallback 14j
                expiry_str = data["data"].get("accessTokenExpiryDate")
                if expiry_str:
                    try:
                        self._token_expiry = datetime.fromisoformat(
                            expiry_str.replace("Z", "+00:00")
                        )
                    except Exception:
                        self._token_expiry = datetime.now(tz=timezone.utc) + timedelta(days=14)
                else:
                    self._token_expiry = datetime.now(tz=timezone.utc) + timedelta(days=14)
                logger.info("CJ token rafraichi (expire %s)", self._token_expiry)
                return self._token
            raise RuntimeError(f"CJ auth failed: {data}")
        except requests.RequestException as e:
            logger.error("CJ auth network error: %s", e)
            raise

    def _headers(self) -> dict:
        return {
            "CJ-Access-Token": self._ensure_token(),
            "Content-Type": "application/json",
        }

    # ------------------------------------------------------------ HTTP CORE
    def _wait_rate_limit(self):
        delta = time.time() - self._last_call_at
        if delta < self._min_interval:
            time.sleep(self._min_interval - delta)
        self._last_call_at = time.time()

    def _request(self, method: str, path: str, retries: int = 3, **kwargs) -> dict:
        url = f"{self.base_url}{path}"
        last_error = None
        for attempt in range(retries):
            try:
                self._wait_rate_limit()
                resp = self.session.request(
                    method,
                    url,
                    headers=self._headers(),
                    timeout=30,
                    **kwargs,
                )
                resp.raise_for_status()
                data = resp.json()
                # Le wrapper CJ : result=True si OK, sinon message d'erreur
                if data.get("result") is False:
                    raise RuntimeError(
                        f"CJ API error: {data.get('message', 'unknown')}"
                    )
                return data
            except requests.RequestException as e:
                last_error = e
                logger.warning(
                    "CJ %s %s attempt %d failed: %s", method, path, attempt + 1, e
                )
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)
        logger.error("CJ %s %s failed after %d attempts", method, path, retries)
        raise last_error

    # --------------------------------------------------------------- PRODUCTS
    def get_product_detail(self, product_id: str) -> dict:
        """Detail complet d'un produit (variants, prix, images, specs)."""
        data = self._request(
            "GET",
            "/api2.0/v1/product/query",
            params={"pid": product_id},
        )
        return data.get("data", {})

    def get_product_stock(self, vid: str) -> int:
        """Stock dispo en entrepot pour une variante.

        Renvoie 0 si rupture, sinon la quantite reservable.
        """
        try:
            data = self._request(
                "GET",
                "/api2.0/v1/product/stock/queryByVid",
                params={"vid": vid},
            )
            items = data.get("data", []) or []
            # Plusieurs entrepots possibles, on prend le total
            total = 0
            for item in items:
                qty = item.get("storageNum") or item.get("quantity") or 0
                try:
                    total += int(qty)
                except (TypeError, ValueError):
                    pass
            return total
        except Exception as e:
            logger.warning("get_product_stock(%s) failed: %s", vid, e)
            return 0

    def list_products(
        self,
        category_id: str = None,
        keyword: str = None,
        page: int = 1,
        page_size: int = 20,
        created_time_from: str = None,
    ) -> list:
        """Liste produits avec filtres."""
        params = {"pageNum": page, "pageSize": page_size}
        if category_id:
            params["categoryId"] = category_id
        if keyword:
            params["productNameEn"] = keyword
        if created_time_from:
            params["createTimeFrom"] = created_time_from
        data = self._request("GET", "/api2.0/v1/product/list", params=params)
        return (data.get("data") or {}).get("list", []) or []

    def list_new_products(self, days: int = 7, category_id: str = None) -> list:
        """Nouveautes catalogue des N derniers jours."""
        since = (datetime.now(tz=timezone.utc) - timedelta(days=days)).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        return self.list_products(
            category_id=category_id, created_time_from=since, page_size=50
        )

    # ----------------------------------------------------------------- ORDERS
    def create_order(
        self,
        order_number: str,
        shipping: dict,
        products: list,
        ship_method: str = "CJPacket Ordinary",
        remark: str = "",
    ) -> dict:
        """Creer une commande dropshipping CJ.

        Args:
            order_number: notre reference (= numero commande WooCommerce)
            shipping: {first_name, last_name, address1, address2, city, zip,
                       state, country_code, phone, email}
            products: [{vid, quantity, ship_price?}]
            ship_method: code transporteur CJ (default CJPacket Ordinary)
            remark: note interne

        Returns: dict avec orderId CJ + status
        """
        payload = {
            "orderNumber": str(order_number),
            "shippingZip": shipping.get("zip", ""),
            "shippingCountryCode": shipping.get("country_code", "FR"),
            "shippingCountry": shipping.get("country", "France"),
            "shippingProvince": shipping.get("state", ""),
            "shippingCity": shipping.get("city", ""),
            "shippingAddress": shipping.get("address1", ""),
            "shippingAddress2": shipping.get("address2", ""),
            "shippingCustomer": (
                f"{shipping.get('first_name', '')} {shipping.get('last_name', '')}"
            ).strip(),
            "shippingPhone": shipping.get("phone", ""),
            "email": shipping.get("email", ""),
            "remark": remark,
            "logisticName": ship_method,
            "products": [
                {"vid": p["vid"], "quantity": p.get("quantity", 1)}
                for p in products
            ],
        }
        data = self._request(
            "POST", "/api2.0/v1/shopping/order/createOrder", json=payload
        )
        return data.get("data", {}) or {}

    def get_order_detail(self, cj_order_id: str) -> dict:
        """Detail commande CJ (status, tracking, total)."""
        data = self._request(
            "GET",
            "/api2.0/v1/shopping/order/getOrderDetail",
            params={"orderId": cj_order_id},
        )
        return data.get("data", {}) or {}

    def get_tracking(self, cj_order_id: str) -> dict:
        """Suivi colis : { trackNumber, logisticName, trackUrl, status }."""
        try:
            data = self._request(
                "GET",
                "/api2.0/v1/logistic/trackInfo",
                params={"orderId": cj_order_id},
            )
            d = data.get("data", {}) or {}
            return {
                "track_number": d.get("trackNumber", ""),
                "logistic_name": d.get("logisticName", ""),
                "track_url": d.get("trackUrl", "")
                or self._build_track_url(d.get("trackNumber", "")),
                "status": d.get("trackStatus", ""),
                "raw": d,
            }
        except Exception as e:
            logger.warning("get_tracking(%s) failed: %s", cj_order_id, e)
            return {}

    @staticmethod
    def _build_track_url(track_number: str) -> str:
        if not track_number:
            return ""
        return f"https://www.17track.net/fr/track#nums={track_number}"

    # ----------------------------------------------------------- LOGISTIQUE
    def get_freight_options(
        self,
        vid: str,
        quantity: int,
        country_code: str = "FR",
        zip_code: str = "75001",
    ) -> list:
        """Renvoie les options de fret avec prix + delais."""
        payload = {
            "products": [{"vid": vid, "quantity": quantity}],
            "countryCode": country_code,
            "zip": zip_code,
        }
        data = self._request(
            "POST", "/api2.0/v1/logistic/freightCalculate", json=payload
        )
        return data.get("data", []) or []
