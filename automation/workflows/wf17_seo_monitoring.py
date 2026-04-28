"""WF17 — SEO monitoring.

Cron : Dimanche 8h Paris.
Track les positions Google de mots-cles cles via DataForSEO,
envoie un rapport hebdo Telegram + log Sheets.

TODO :
- Configurer DATAFORSEO_LOGIN/PASSWORD
- Liste de keywords a tracker (fichier JSON / config)
- dataforseo.serp.organic.live(keyword, lang='fr', loc='France')
- Detecter changements de position (delta vs semaine precedente)
- Telegram alert si chute > 5 positions sur top keyword
"""
import logging
from automation.utils.error_handling import workflow_handler
from automation.workflows import get_telegram

log = logging.getLogger("automation.wf17")


@workflow_handler("wf17_seo_monitoring")
def run():
    tg = get_telegram()
    # PSEUDO-CODE :
    # keywords = ["chargeur magsafe 3-en-1", "trottinette electrique premium", ...]
    # for kw in keywords:
    #    rank = dataforseo.get_rank(kw, domain='gavio.fr')
    #    history.update(kw, rank)
    # report = compute_deltas(history)
    # tg.send_message(format_report(report))

    log.info("WF17 SEO monitoring : a implementer")
    return {"status": "skipped", "reason": "skeleton"}
