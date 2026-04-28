"""WF15 — Newsletter mensuelle.

Cron : 1er du mois 10h30 Paris.
Compile :
  - 3 nouveaux produits du mois
  - 3 articles blog les plus lus
  - Promo en cours
Envoie a tous les abonnes Brevo (liste 'newsletter').

TODO : genere HTML template Apple-like, envoie via brevo.send_campaign
"""
import logging
from automation.utils.error_handling import workflow_handler
from automation.workflows import get_brevo, get_telegram

log = logging.getLogger("automation.wf15")


@workflow_handler("wf15_newsletter")
def run():
    brevo = get_brevo()
    tg = get_telegram()

    if not brevo:
        log.info("WF15 desactive : BREVO_API_KEY non configure")
        return {"status": "skipped", "reason": "no_brevo_key"}

    # PSEUDO-CODE :
    # 1. wc.get_products(orderby='date', order='desc', per_page=3)
    # 2. articles = wp.get_posts(orderby='views', per_page=3)  # via plugin views
    # 3. promo = config.current_promo (env CURRENT_PROMO_CODE)
    # 4. Compile HTML template
    # 5. brevo.send_campaign(name='Newsletter Gavio Mois X', list_ids=[NL_LIST_ID])
    # 6. brevo.send_campaign_now(campaign_id)

    log.info("WF15 Newsletter : a implementer")
    return {"status": "skipped", "reason": "skeleton"}
