"""WF11 — Posts TikTok.

Cron : 13h + 20h Paris.
Genere video courte produit via Kie.ai Seedance, publie via Ayrshare ou
TikTok Display API.

TODO :
- Selection produit du jour
- Generation script court (15-30s) avec Claude
- Generation video Seedance (Kie.ai) ou stock + voiceover Google TTS
- Sous-titres + musique trending
- Upload via Ayrshare API (si AYRSHARE_API_KEY present)
"""
import logging
from automation.utils.error_handling import workflow_handler
from automation.workflows import get_telegram

log = logging.getLogger("automation.wf11")


@workflow_handler("wf11_tiktok")
def run():
    tg = get_telegram()

    # PSEUDO-CODE :
    # 1. Pick product (rotation)
    # 2. claude.generate script 15-30s (hook + 3 features + CTA)
    # 3. kie.generate video Seedance OR ffmpeg stock + tts
    # 4. ayrshare.post(platforms=['tiktok'], video_url, caption, hashtags)
    # 5. Telegram avec lien post

    log.info("WF11 TikTok : a implementer")
    tg.send_message(
        "ℹ️ WF11 TikTok : workflow squelette, "
        "configurer AYRSHARE_API_KEY ou TIKTOK_ACCESS_TOKEN avant activation"
    )
    return {"status": "skipped", "reason": "skeleton"}
