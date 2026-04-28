"""WF03 — Remboursement.

Webhook : demande de remboursement.
Notifie le manager via Telegram avec 3 boutons (rembourser/info/refuser).
TODO : integration Stripe pour le remboursement effectif.
"""
import logging
from datetime import datetime
from uuid import uuid4
from zoneinfo import ZoneInfo

from automation.config import Config
from automation.utils.error_handling import workflow_handler
from automation.workflows import get_wc, get_telegram

log = logging.getLogger("automation.wf03")
PARIS = ZoneInfo("Europe/Paris")
RETRACTATION_DAYS = 14


def _on_decision(action: str, ctx: dict):
    wc = get_wc()
    tg = get_telegram()
    order_id = ctx["order_id"]
    order_number = ctx["order_number"]

    if action == "refund":
        # TODO: stripe.refund(stripe_payment_id, amount=ctx['total'])
        wc.update_order(order_id, {"status": "refunded"})
        tg.send_message(
            f"\U0001f4b8 Remboursement {ctx['total_fmt']} effectue pour #{order_number}"
            f" (TODO : confirmer cote Stripe)"
        )
    elif action == "info":
        wc.add_order_note(
            order_id,
            "Bonjour, nous avons bien recu votre demande. Pourriez-vous nous "
            "donner plus de details sur le motif ?",
            customer_note=True,
        )
        tg.send_message(f"ℹ️ Info demandee au client pour #{order_number}")
    elif action == "refuse":
        wc.add_order_note(
            order_id,
            "Apres examen, nous ne sommes pas en mesure de proceder au "
            "remboursement. Contactez-nous pour plus d'informations.",
            customer_note=True,
        )
        tg.send_message(f"❌ Remboursement refuse pour #{order_number}")
    elif action == "timeout":
        tg.send_message(
            f"⏰ Rappel : demande remboursement #{order_number} en attente depuis 48h"
        )


@workflow_handler("wf03_remboursement")
def process_refund_request(data: dict, decision_store):
    wc = get_wc()
    tg = get_telegram()

    order_id = data.get("order_id") or data.get("body", {}).get("order_id")
    motif = data.get("motif", data.get("body", {}).get("motif", "Non specifie"))

    if not order_id:
        log.error("Refund request without order_id")
        return

    order = wc.get_order(order_id)
    billing = order.get("billing", {}) or {}
    meta = {m["key"]: m["value"] for m in order.get("meta_data", []) or []}
    total = float(order.get("total", 0))

    date_created = order.get("date_created", "")
    try:
        order_date = datetime.fromisoformat(date_created.replace("Z", "+00:00"))
        days_since = (datetime.now(tz=PARIS) - order_date.astimezone(PARIS)).days
    except Exception:
        days_since = 0

    within = days_since <= RETRACTATION_DAYS
    retract_text = (
        f"✅ Dans le delai ({days_since}j / {RETRACTATION_DAYS}j)" if within
        else f"❌ Hors delai ({days_since}j > {RETRACTATION_DAYS}j)"
    )

    products_lines = [
        f"• {item.get('quantity', 1)}x {item.get('name', 'Produit')}"
        for item in order.get("line_items", []) or []
    ]
    products_text = "\n".join(products_lines) or "Aucun produit"

    client_name = f"{billing.get('first_name', '')} {billing.get('last_name', '')}".strip()
    order_number = order.get("number", order_id)
    total_fmt = f"{total:.2f}€"

    ctx = {
        "order_id": order_id,
        "order_number": order_number,
        "client_name": client_name,
        "client_email": billing.get("email", ""),
        "total": total,
        "total_fmt": total_fmt,
        "stripe_payment_id": meta.get("_stripe_intent_id", "")
        or order.get("transaction_id", ""),
        "motif": motif,
    }

    decision_id = f"refund-{order_id}-{uuid4().hex[:8]}"
    callback = f"{Config.WEBHOOK_BASE_URL}/decision/{decision_id}"
    keyboard = [[
        {"text": "✅ Rembourser", "url": f"{callback}?action=refund"},
        {"text": "ℹ️ Info", "url": f"{callback}?action=info"},
        {"text": "❌ Refuser", "url": f"{callback}?action=refuse"},
    ]]

    msg = (
        f"\U0001f504 *Demande de remboursement*\n\n"
        f"\U0001f4cb #{order_number}\n"
        f"\U0001f464 {client_name} ({billing.get('email', '')})\n"
        f"\U0001f4c5 il y a {days_since} jours\n"
        f"\U0001f4b0 {total_fmt}\n\n"
        f"\U0001f4e6 Produits :\n{products_text}\n\n"
        f"\U0001f4ac Motif : \"{motif}\"\n\n"
        f"⏱️ Retractation : {retract_text}"
    )
    tg.send_message(msg, inline_keyboard=keyboard)
    decision_store.create(
        decision_id=decision_id,
        context=ctx,
        callback=_on_decision,
        timeout_seconds=48 * 3600,
    )
    log.info("Refund #%s sent for review", order_number)
