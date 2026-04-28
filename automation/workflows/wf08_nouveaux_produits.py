"""WF08 — Detection nouveaux produits CJ.

Cron : Dimanche 10h Paris.
Detecte les nouveaux produits CJ dans les categories Gavio (hi-tech / hi-ticket),
envoie une notif Telegram pour validation manuelle (pas d'import auto pour
preserver la curation premium de Gavio).

TODO : implementer la logique complete une fois les category IDs CJ identifies
       cote Gavio. Pour l'instant : squelette + pseudo-code commente.
"""
import logging

from automation.utils.error_handling import workflow_handler
from automation.workflows import get_cj, get_telegram

log = logging.getLogger("automation.wf08")

# Categories CJ a surveiller (a valider apres exploration catalogue CJ)
CJ_CATEGORIES_HI_TECH = [
    # ID a remplir : "Smart Home", "Mobility", "Audio", "Drones", "Wearables"
    # voir https://developers.cjdropshipping.com/api2.0/v1/category/getCategory
]


@workflow_handler("wf08_nouveaux_produits")
def run():
    cj = get_cj()
    tg = get_telegram()

    # PSEUDO-CODE :
    # 1. Pour chaque category_id de CJ_CATEGORIES_HI_TECH :
    #    new = cj.list_new_products(days=7, category_id=category_id)
    # 2. Filtrer :
    #    - cout fournisseur entre $30 et $1100
    #    - rating CJ >= 4 etoiles
    #    - description en EN traduite -> FR (Claude)
    # 3. Pour chaque candidat, envoyer un message Telegram avec :
    #    - photo principale (sendPhoto)
    #    - prix CJ + prix de vente suggere (cout * 2.2)
    #    - lien CJ
    #    - boutons : "Importer" / "Skip" (callback)
    # 4. Sur "Importer" : creer le produit dans WC (draft) avec _cj_vid

    if not CJ_CATEGORIES_HI_TECH:
        log.info("WF08 : pas de category_id configures, skip")
        tg.send_message(
            "ℹ️ WF08 Nouveaux produits : configurer CJ_CATEGORIES_HI_TECH "
            "dans wf08_nouveaux_produits.py avant activation"
        )
        return {"status": "skipped"}

    new_total = 0
    for cat_id in CJ_CATEGORIES_HI_TECH:
        try:
            new_items = cj.list_new_products(days=7, category_id=cat_id)
            log.info("Cat %s : %d nouveautes", cat_id, len(new_items))
            new_total += len(new_items)
            # TODO : envoyer un message par produit (avec sendPhoto + bouton)
        except Exception as e:
            log.warning("Cat %s failed: %s", cat_id, e)

    tg.send_message(
        f"\U0001f50d *Veille produits CJ — Gavio*\n\n"
        f"{new_total} nouveaute(s) detectee(s) cette semaine.\n"
        f"_Validation manuelle requise (TODO : interface)._"
    )
    return {"status": "ok", "found": new_total}
