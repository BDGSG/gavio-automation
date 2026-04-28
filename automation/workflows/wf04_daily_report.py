"""WF04 — Rapport quotidien.

Cron : 20h00 Paris.
Envoie un resume de la journee : commandes, CA, marge estimee, statuts, top produit.
"""
import logging
from collections import Counter
from datetime import datetime
from zoneinfo import ZoneInfo

from automation.utils.error_handling import workflow_handler
from automation.workflows import get_wc, get_telegram

log = logging.getLogger("automation.wf04")
PARIS = ZoneInfo("Europe/Paris")

# Marge moyenne estimee Gavio (apres frais transport CJ + Stripe)
MARGE_MOYENNE = 0.40


@workflow_handler("wf04_daily_report")
def run():
    wc = get_wc()
    tg = get_telegram()

    now = datetime.now(tz=PARIS)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = now.replace(hour=23, minute=59, second=59, microsecond=0)

    orders = wc.get_orders(after=start.isoformat(), before=end.isoformat(), per_page=100)

    nb = len(orders)
    ca = sum(float(o.get("total", 0) or 0) for o in orders)
    marge = round(ca * MARGE_MOYENNE, 2)

    statuses = Counter(o.get("status", "unknown") for o in orders)
    products_count = Counter()
    for o in orders:
        for item in o.get("line_items", []) or []:
            products_count[item.get("name", "?")] += item.get("quantity", 1)

    top_product, top_qty = ("Aucun", 0)
    if products_count:
        top_product, top_qty = products_count.most_common(1)[0]

    msg = (
        f"\U0001f4ca *Rapport quotidien — Gavio*\n"
        f"\U0001f4c5 {now.strftime('%d/%m/%Y')}\n\n"
        f"\U0001f6cd️ Commandes : {nb}\n"
        f"\U0001f4b0 CA : {ca:.2f}€\n"
        f"\U0001f4b8 Marge estimee : ~{marge:.2f}€\n\n"
        f"✅ Processing : {statuses.get('processing', 0)}\n"
        f"⚠️ On-hold : {statuses.get('on-hold', 0)}\n"
        f"\U0001f4e6 Completed : {statuses.get('completed', 0)}\n"
        f"\U0001f504 Refunded : {statuses.get('refunded', 0)}\n"
        f"❌ Cancelled : {statuses.get('cancelled', 0)}\n\n"
        f"\U0001f3c6 Top produit : {top_product} ({top_qty} ventes)"
    )
    tg.send_message(msg)
    log.info("Daily report sent: %d orders, %.2f€", nb, ca)
    return {"status": "ok", "orders": nb, "ca": ca}
