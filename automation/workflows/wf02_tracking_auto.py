"""WF02 — Tracking Auto CJ.

Cron toutes les 4h.
Pour chaque commande WooCommerce 'processing' deja transmise a CJ
(meta `_cj_order_id`), interroge l'API CJ pour recuperer le tracking,
met a jour la commande WC et envoie email + Telegram.
"""
import logging
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from automation.utils.error_handling import workflow_handler
from automation.workflows import get_cj, get_wc, get_telegram, get_resend

log = logging.getLogger("automation.wf02")
PARIS = ZoneInfo("Europe/Paris")
LATE_DAYS = 7


def _email_tracking(client_name: str, order_number: str, track_no: str, track_url: str) -> str:
    return (
        f"<p>Bonjour {client_name},</p>"
        f"<p>Bonne nouvelle : votre commande <strong>#{order_number}</strong> a ete expediee.</p>"
        f"<p><strong>Numero de suivi :</strong> {track_no}</p>"
        f"<p><a href='{track_url}'>Suivre mon colis</a></p>"
        f"<p>Delai de livraison estime : 7 a 15 jours ouvres.</p>"
        f"<p>Toute l'equipe Gavio vous remercie pour votre confiance.</p>"
    )


@workflow_handler("wf02_tracking_auto")
def run():
    cj = get_cj()
    wc = get_wc()
    tg = get_telegram()
    resend = get_resend()

    orders = wc.get_orders(status="processing", per_page=50)
    if not orders:
        log.info("Aucune commande processing")
        return {"status": "ok", "completed": 0, "waiting": 0, "late": 0}

    completed, waiting, late = [], [], []

    for order in orders:
        order_id = order["id"]
        order_number = order.get("number", order_id)
        meta = {m["key"]: m["value"] for m in order.get("meta_data", []) or []}

        cj_order_id = meta.get("_cj_order_id", "")
        existing_track = meta.get("_tracking_number", "")

        if existing_track:
            # Deja traite, on skip
            continue

        if not cj_order_id:
            # Pas encore transmise a CJ → c'est le boulot de WF07, on note juste
            try:
                date_created = order.get("date_created", "")
                order_date = datetime.fromisoformat(date_created.replace("Z", "+00:00"))
                days = (datetime.now(tz=timezone.utc) - order_date).days
                if days > LATE_DAYS:
                    late.append({"order": order, "days": days, "reason": "non transmise CJ"})
                else:
                    waiting.append(order)
            except Exception:
                waiting.append(order)
            continue

        # Interroge CJ pour le tracking
        try:
            tracking = cj.get_tracking(cj_order_id)
        except Exception as e:
            log.error("CJ tracking failed for order #%s (cj_id=%s): %s", order_number, cj_order_id, e)
            waiting.append(order)
            continue

        track_no = tracking.get("track_number", "")
        track_url = tracking.get("track_url", "")

        if not track_no:
            # Toujours en attente d'expedition
            try:
                date_created = order.get("date_created", "")
                order_date = datetime.fromisoformat(date_created.replace("Z", "+00:00"))
                days = (datetime.now(tz=timezone.utc) - order_date).days
                if days > LATE_DAYS:
                    late.append({"order": order, "days": days, "reason": "CJ pas encore expedie"})
                else:
                    waiting.append(order)
            except Exception:
                waiting.append(order)
            continue

        # On a un numero de suivi
        try:
            wc.update_order_meta(order_id, "_tracking_number", track_no)
            if track_url:
                wc.update_order_meta(order_id, "_tracking_url", track_url)
            wc.update_order(order_id, {"status": "completed"})

            billing = order.get("billing", {}) or {}
            client_name = f"{billing.get('first_name', '')} {billing.get('last_name', '')}".strip()

            wc.add_order_note(
                order_id,
                (
                    f"\U0001f4e6 Votre commande a ete expediee !\n"
                    f"Numero de suivi : {track_no}\n"
                    f"Suivre mon colis : {track_url or 'N/A'}"
                ),
                customer_note=True,
            )

            # Email Resend
            try:
                if billing.get("email"):
                    resend.send_template(
                        to=billing["email"],
                        subject=f"Votre commande Gavio #{order_number} est en route",
                        title="Votre commande est expediee",
                        body_html=_email_tracking(
                            client_name or "client", order_number, track_no, track_url
                        ),
                        cta_label="Suivre mon colis",
                        cta_url=track_url,
                    )
            except Exception as e:
                log.warning("Email tracking failed for #%s: %s", order_number, e)

            completed.append(order)
            tg.send_message(
                f"✅ *Commande #{order_number} — EXPEDIEE*\n\n"
                f"\U0001f464 {client_name}\n"
                f"\U0001f4b0 {order.get('total', '?')}€\n"
                f"\U0001f4e6 `{track_no}`\n"
                f"\U0001f517 {track_url or 'N/A'}\n"
                f"✅ Statut WC : completed\n"
                f"\U0001f4e7 Email client envoye"
            )
            log.info("Order #%s -> completed (tracking %s)", order_number, track_no)
        except Exception as e:
            log.error("Failed to complete order #%s: %s", order_number, e)

    # Alerte commandes en retard
    for item in late:
        billing = item["order"].get("billing", {}) or {}
        name = f"{billing.get('first_name', '')} {billing.get('last_name', '')}".strip()
        tg.send_message(
            f"⚠️ *Commande en retard — {item['days']} jours*\n"
            f"#{item['order'].get('number', item['order']['id'])} — {name}\n"
            f"Cause : {item['reason']}"
        )

    # Resume
    total = len(orders)
    if total > 0:
        tg.send_message(
            f"\U0001f4ca *Tracking — Gavio*\n\n"
            f"✅ {len(completed)} expediee(s)\n"
            f"⏳ {len(waiting)} en attente\n"
            f"⚠️ {len(late)} en retard (>{LATE_DAYS}j)\n\n"
            f"Total processing : {total}"
        )

    return {
        "status": "ok",
        "completed": len(completed),
        "waiting": len(waiting),
        "late": len(late),
    }
