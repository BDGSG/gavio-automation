"""WF01 — Commande Auto.

Webhook trigger : nouvelle commande WooCommerce.
- Verifications anti-fraude
- Si OK : notif Telegram + creation commande CJ Dropshipping (cf WF07 differable)
- Si KO : commande mise on-hold + Telegram avec boutons de validation
"""
import logging
import re
from datetime import datetime
from uuid import uuid4
from zoneinfo import ZoneInfo

from automation.config import Config
from automation.utils.error_handling import workflow_handler
from automation.workflows import get_wc, get_telegram

log = logging.getLogger("automation.wf01")
PARIS = ZoneInfo("Europe/Paris")

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def _extract(order: dict) -> dict:
    """Normalise les champs WooCommerce utiles."""
    billing = order.get("billing", {}) or {}
    shipping = order.get("shipping", {}) or {}
    meta = {m["key"]: m["value"] for m in order.get("meta_data", []) or []}

    products, lines = [], []
    for item in order.get("line_items", []) or []:
        p = {
            "name": item.get("name", ""),
            "sku": item.get("sku", ""),
            "qty": item.get("quantity", 1),
            "price": item.get("total", "0"),
            "meta": {m["key"]: m["value"] for m in item.get("meta_data", []) or []},
        }
        products.append(p)
        lines.append(f"• {p['qty']}x {p['name']} ({p['sku']}) — {p['price']}€")

    total = float(order.get("total", 0) or 0)
    return {
        "order_id": order.get("id"),
        "order_number": order.get("number") or order.get("id"),
        "date_created": order.get("date_created", ""),
        "total": total,
        "total_fmt": f"{total:.2f}€",
        "payment_method": order.get("payment_method_title", ""),
        "client_name": f"{billing.get('first_name', '')} {billing.get('last_name', '')}".strip(),
        "client_email": billing.get("email", ""),
        "client_phone": billing.get("phone", ""),
        "shipping_country": shipping.get("country", ""),
        "shipping_city": shipping.get("city", ""),
        "shipping_address": (
            f"{shipping.get('address_1', '')} {shipping.get('address_2', '')}\n"
            f"{shipping.get('postcode', '')} {shipping.get('city', '')}\n"
            f"{shipping.get('country', '')}"
        ).strip(),
        "products": products,
        "products_text": "\n".join(lines) or "Aucun produit",
        "stripe_payment_id": meta.get("_stripe_intent_id", "")
        or meta.get("_transaction_id", "")
        or order.get("transaction_id", ""),
    }


def _antifraud(order: dict) -> tuple:
    issues = []
    if order["total"] <= 0:
        issues.append("Montant <= 0")
    if not EMAIL_RE.match(order["client_email"]):
        issues.append(f"Email invalide : {order['client_email']}")
    country = (order["shipping_country"] or "").upper()
    if country and country not in Config.FRAUD_ALLOWED_COUNTRIES:
        issues.append(f"Pays non autorise : {country}")
    if order["total"] > Config.FRAUD_MAX_AMOUNT:
        issues.append(
            f"Montant ({order['total_fmt']}) > seuil ({Config.FRAUD_MAX_AMOUNT}€)"
        )
    return (len(issues) == 0, issues)


def _on_decision(action: str, ctx: dict):
    """Callback boutons Telegram (approve / cancel / timeout)."""
    wc = get_wc()
    tg = get_telegram()
    order_id = ctx["order_id"]
    order_number = ctx["order_number"]

    if action == "approve":
        wc.update_order(order_id, {"status": "processing"})
        wc.add_order_note(
            order_id,
            "[GAVIO] Commande validee manuellement malgre echec verifications.",
            customer_note=False,
        )
        tg.send_message(f"✅ Commande #{order_number} validee manuellement.")
        log.info("Order #%s manually approved", order_number)

    elif action in ("cancel", "timeout"):
        wc.update_order(order_id, {"status": "cancelled"})
        # TODO : si stripe_payment_id present -> rembourser via Stripe
        suffix = " (timeout 24h)" if action == "timeout" else ""
        tg.send_message(
            f"❌ Commande #{order_number} annulee{suffix}. "
            f"Penser a verifier Stripe pour remboursement."
        )
        log.info("Order #%s cancelled (action=%s)", order_number, action)


@workflow_handler("wf01_commande_auto")
def process_order(order_data: dict, decision_store):
    """Traite une commande WooCommerce. Appelee depuis le webhook."""
    wc = get_wc()
    tg = get_telegram()

    order = _extract(order_data)
    if not order["order_id"]:
        log.warning("Webhook sans order_id, ignore")
        return

    log.info("Processing order #%s (%s)", order["order_number"], order["total_fmt"])

    ok, issues = _antifraud(order)

    if ok:
        # Happy path
        now = datetime.now(tz=PARIS).strftime("%d/%m/%Y %H:%M")
        wc.add_order_note(
            order["order_id"],
            f"[GAVIO] Commande validee automatiquement le {now}. Anti-fraude OK.",
            customer_note=False,
        )
        msg = (
            f"\U0001f6cd️ *Nouvelle commande #{order['order_number']}*\n\n"
            f"\U0001f464 {order['client_name']} — {order['client_email']}\n"
            f"\U0001f4cd {order['shipping_address']}\n"
            f"\U0001f4b0 {order['total_fmt']} ({order['payment_method']})\n\n"
            f"\U0001f4e6 Produits :\n{order['products_text']}\n\n"
            f"_Transmission CJ via WF07 dans les 15 min._"
        )
        tg.send_message(msg)
        log.info("Order #%s auto-validated", order["order_number"])
    else:
        # Block + ask manual decision
        wc.update_order(order["order_id"], {"status": "on-hold"})
        decision_id = f"order-{order['order_id']}-{uuid4().hex[:8]}"
        callback = f"{Config.WEBHOOK_BASE_URL}/decision/{decision_id}"
        keyboard = [[
            {"text": "✅ Forcer validation", "url": f"{callback}?action=approve"},
            {"text": "❌ Annuler", "url": f"{callback}?action=cancel"},
        ]]
        issues_txt = "\n".join(f"❌ {i}" for i in issues)
        msg = (
            f"⚠️ *Commande #{order['order_number']} — VERIF ECHOUEE*\n\n"
            f"\U0001f464 {order['client_name']} — {order['client_email']}\n"
            f"\U0001f4b0 {order['total_fmt']}\n\n"
            f"Probleme(s) :\n{issues_txt}\n\n"
            f"⏸️ Commande on-hold."
        )
        tg.send_message(msg, inline_keyboard=keyboard)
        decision_store.create(
            decision_id=decision_id,
            context=order,
            callback=_on_decision,
            timeout_seconds=24 * 3600,
        )
        log.info("Order #%s on-hold, awaiting decision", order["order_number"])
