"""WF13 — Enrichissement FAQ produits.

Cron : Dimanche 11h Paris.
Pour chaque produit, genere/enrichit la FAQ via Claude
(en se basant sur les questions support recurrentes + meta description CJ).

TODO :
- Recuperer les produits avec FAQ vide ou < 3 questions
- claude.generate FAQ structuree (5-7 Q/R) en se basant sur :
  - description CJ (specs, materiaux, dimensions)
  - questions Reddit/Quora pour la categorie
- Mettre a jour le champ ACF/meta `_faq_questions` du produit
- WP cache flush
"""
import logging
from automation.utils.error_handling import workflow_handler
from automation.workflows import get_telegram

log = logging.getLogger("automation.wf13")


@workflow_handler("wf13_faq_enrichment")
def run():
    tg = get_telegram()

    # PSEUDO-CODE :
    # 1. wc.get_products(meta_query: faq_count < 3)
    # 2. Pour chaque produit :
    #    cj_data = cj.get_product_detail(product._cj_pid)
    #    faq = claude.generate("genere 5-7 Q/R en FR pour ce produit", cj_data)
    #    wc.update_product(id, {meta_data: [{key:'_faq_questions', value: faq}]})
    # 3. Telegram resume

    log.info("WF13 FAQ enrichment : a implementer")
    return {"status": "skipped", "reason": "skeleton"}
