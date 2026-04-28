"""WF18 — Veille concurrentielle.

Cron : Lundi 7h Paris.
Pour chaque produit Gavio, scrape Amazon FR, Fnac, Boulanger
pour comparer prix + stock + nouveaux entrants.

TODO :
- Ajouter `_competitor_urls` JSON sur chaque produit WC
- Pour chaque produit : scrape amazon.fr (price + Buy Box), fnac.com, boulanger.com
- Si concurrent moins cher de >10% : alerte Telegram + suggestion baisse prix
- Si concurrent en rupture : opportunite mise en avant
"""
import logging
from automation.utils.error_handling import workflow_handler
from automation.workflows import get_telegram

log = logging.getLogger("automation.wf18")


@workflow_handler("wf18_concurrence")
def run():
    tg = get_telegram()
    # PSEUDO-CODE :
    # for product in wc.get_products(meta_key='_competitor_urls'):
    #     for url in product.competitor_urls:
    #         price, in_stock = scrape(url)  # bs4 + headers anti-bot
    #         if price < product.price * 0.9:
    #             alerts.append(f"{product.name}: amazon {price}€ < nous {product.price}€")
    # if alerts: tg.send_message(format_alerts(alerts))

    log.info("WF18 Concurrence : a implementer")
    return {"status": "skipped", "reason": "skeleton"}
