"""WF07 — Transmission Commandes vers CJ Dropshipping.

Cron toutes les 15 min.
Pour chaque commande WooCommerce 'processing' sans meta `_cj_order_id`,
cree la commande chez CJ via leur API et stocke l'ID renvoye.
"""
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from automation.utils.error_handling import workflow_handler
from automation.workflows import get_cj, get_wc, get_telegram

log = logging.getLogger("automation.wf07")
PARIS = ZoneInfo("Europe/Paris")


def _build_cj_payload(order: dict) -> tuple:
    """Convertit une commande WC en payload CJ (shipping + products).

    Returns: (shipping_dict, products_list, sku_warnings)
    """
    billing = order.get("billing", {}) or {}
    shipping_wc = order.get("shipping", {}) or {}

    shipping = {
        "first_name": shipping_wc.get("first_name") or billing.get("first_name", ""),
        "last_name": shipping_wc.get("last_name") or billing.get("last_name", ""),
        "address1": shipping_wc.get("address_1", ""),
        "address2": shipping_wc.get("address_2", ""),
        "city": shipping_wc.get("city", ""),
        "zip": shipping_wc.get("postcode", ""),
        "state": shipping_wc.get("state", ""),
        "country_code": shipping_wc.get("country", "FR") or "FR",
        "country": shipping_wc.get("country", "France"),
        "phone": billing.get("phone", ""),
        "email": billing.get("email", ""),
    }

    # Pour chaque ligne : on cherche le meta `_cj_vid` cote PRODUIT
    # (le SKU WooCommerce ne suffit pas pour CJ — il faut le variant ID)
    products = []
    warnings = []
    for item in order.get("line_items", []) or []:
        # item["product_id"] et item["variation_id"] sont WC, mais on
        # stocke `_cj_vid` au niveau du produit dans WC
        vid = ""
        # 1. Cherche dans meta_data de l'item (si l'admin l'a stocke la)
        for m in item.get("meta_data", []) or []:
            if m.get("key") == "_cj_vid":
                vid = str(m.get("value") or "")
                break
        # 2. Sinon on doit recuperer le produit WC pour son meta
        if not vid:
            from automation.workflows import get_wc
            wc = get_wc()
            prod = wc.get_product(item.get("product_id"))
            if prod:
                for m in prod.get("meta_data", []) or []:
                    if m.get("key") == "_cj_vid":
                        vid = str(m.get("value") or "")
                        break

        if not vid:
            warnings.append(
                f"SKU {item.get('sku', '?')} : aucun _cj_vid trouve"
            )
            continue

        products.append({
            "vid": vid,
            "quantity": item.get("quantity", 1),
        })

    return shipping, products, warnings


@workflow_handler("wf07_transmission_cj")
def run():
    cj = get_cj()
    wc = get_wc()
    tg = get_telegram()

    processing = wc.get_orders(status="processing", per_page=50)
    if not processing:
        return {"status": "ok", "submitted": 0}

    pending = []
    for order in processing:
        meta_keys = {m["key"] for m in order.get("meta_data", []) or []}
        if "_cj_order_id" not in meta_keys:
            pending.append(order)

    if not pending:
        log.info("Aucune commande a transmettre")
        return {"status": "ok", "submitted": 0}

    log.info("Transmission CJ : %d commande(s) a soumettre", len(pending))

    submitted = 0
    failed = 0

    for order in pending:
        order_id = order["id"]
        order_number = order.get("number", order_id)
        billing = order.get("billing", {}) or {}
        client_name = f"{billing.get('first_name', '')} {billing.get('last_name', '')}".strip()

        shipping, products, warnings = _build_cj_payload(order)

        if not products:
            failed += 1
            tg.send_message(
                f"⚠️ *Commande #{order_number} — echec transmission CJ*\n\n"
                f"\U0001f464 {client_name}\n"
                f"❌ Aucun variant CJ trouve sur les lignes\n\n"
                f"_Details :\n" + "\n".join(warnings) + "_\n\n"
                f"_Ajouter le meta `_cj_vid` aux produits WC concernes._"
            )
            continue

        try:
            res = cj.create_order(
                order_number=str(order_number),
                shipping=shipping,
                products=products,
                ship_method="CJPacket Ordinary",
                remark=f"Order Gavio #{order_number}",
            )
            cj_order_id = (
                res.get("orderId")
                or res.get("orderID")
                or res.get("orderNum")
                or ""
            )

            if not cj_order_id:
                raise RuntimeError(f"Reponse CJ sans orderId : {res}")

            wc.update_order_meta(order_id, "_cj_order_id", str(cj_order_id))
            wc.update_order_meta(
                order_id,
                "_cj_submitted_at",
                datetime.now(tz=PARIS).isoformat(),
            )
            wc.add_order_note(
                order_id,
                f"[CJ] Commande transmise — CJ orderId : {cj_order_id}",
                customer_note=False,
            )
            submitted += 1
            tg.send_message(
                f"\U0001f6cd️ *Commande #{order_number} transmise a CJ*\n\n"
                f"\U0001f464 {client_name}\n"
                f"\U0001f4b0 {order.get('total', '?')}€\n"
                f"\U0001f194 CJ : `{cj_order_id}`\n"
                f"\U0001f4e6 {len(products)} ligne(s)\n\n"
                f"_Tracking attendu sous 24-72h (WF02)._"
            )
            log.info("Order #%s -> CJ %s", order_number, cj_order_id)

            if warnings:
                tg.send_message(
                    f"⚠️ #{order_number} — alertes :\n" + "\n".join(warnings)
                )

        except Exception as e:
            failed += 1
            tg.send_message(
                f"❌ *Echec CJ — Commande #{order_number}*\n\n"
                f"\U0001f464 {client_name}\n"
                f"Erreur : `{str(e)[:200]}`\n\n"
                f"_Verifier manuellement sur cjdropshipping.com_"
            )
            log.error("CJ submit failed for #%s: %s", order_number, e)

    return {"status": "ok", "submitted": submitted, "failed": failed}
