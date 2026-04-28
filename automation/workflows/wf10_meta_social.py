"""WF10 — Posts Meta (Facebook + Instagram).

Cron : 12h Paris quotidien.
Rotation produits stars (1 par jour). Genere caption + visuel via Claude/Kie,
publie sur FB Page + IG Business Account via Graph API.

TODO :
- Configurer META_PAGE_ACCESS_TOKEN, META_PAGE_ID, META_IG_USER_ID
- Selection produit du jour (rotation par sales rank ou tag 'star')
- Generation caption FR Claude (hook + features + CTA + 5 hashtags)
- Generation visuel carre 1080x1080 Kie.ai FLUX
- Upload image -> Graph API container -> publish
"""
import logging
from automation.utils.error_handling import workflow_handler
from automation.workflows import get_telegram

log = logging.getLogger("automation.wf10")


@workflow_handler("wf10_meta_social")
def run():
    tg = get_telegram()

    # PSEUDO-CODE :
    # 1. Selection produit du jour (rotation, ou tag 'star' WC)
    # 2. claude.generate caption FR (max 2200 chars FB, 2200 IG)
    # 3. kie.generate image 1080x1080 (flux-pro)
    # 4. POST Graph API : /{ig_user_id}/media (container) puis /media_publish
    # 5. POST Graph API : /{page_id}/photos (FB)
    # 6. Telegram confirmation

    log.info("WF10 Meta social : a implementer")
    tg.send_message(
        "ℹ️ WF10 Meta social : workflow squelette, "
        "configurer META_PAGE_ACCESS_TOKEN avant activation"
    )
    return {"status": "skipped", "reason": "skeleton"}
