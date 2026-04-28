"""WF21 — Google Shopping feed optimization.

Cron : 5h00 quotidien.
Genere un feed XML/CSV optimise pour Google Merchant Center :
  - title : SKU + brand + features clefs (max 150 chars)
  - description : 500 chars optimisees
  - price : prix actuel + sale_price si promo
  - availability : in_stock / out_of_stock (sync via WF06)
  - gtin / mpn : si dispo
  - shipping : 5,90€ standard FR

TODO :
- Generer feed.xml via XML/CSV WC + transformations
- Upload SFTP / GCS pour MGC
- Optimiser titres (Claude) si CTR < seuil
"""
import logging
from automation.utils.error_handling import workflow_handler
from automation.workflows import get_telegram

log = logging.getLogger("automation.wf21")


@workflow_handler("wf21_google_shopping")
def run():
    tg = get_telegram()
    # PSEUDO-CODE :
    # products = wc.get_products(status='publish')
    # feed_items = [build_gmc_item(p) for p in products]
    # xml = render_xml(feed_items)
    # write to /data/gavio_feed/feed.xml
    # GMC pull via URL feed (config dans Merchant Center)

    log.info("WF21 Google Shopping : a implementer")
    return {"status": "skipped", "reason": "skeleton"}
