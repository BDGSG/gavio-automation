"""Gavio Automation - Entry point.

Demarre :
- APScheduler pour les workflows planifies (cron)
- Flask pour les webhooks (WooCommerce, Stripe)

Usage : python -m automation
"""
import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from pytz import timezone

from automation.config import Config
from automation.utils.logging import setup_logging
from automation.workflows import init_clients
from automation.workflows import (
    wf02_tracking_auto,
    wf04_daily_report,
    wf05_blog_seo,
    wf06_sync_stock_cj,
    wf07_transmission_cj,
    wf08_nouveaux_produits,
    wf10_meta_social,
    wf11_tiktok,
    wf12_monitoring,
    wf13_faq_enrichment,
    wf14_brevo_emails,
    wf15_newsletter,
    wf17_seo_monitoring,
    wf18_concurrence,
    wf21_google_shopping,
    wf22_wp_maintenance,
)
from automation.web.app import app

PARIS = timezone("Europe/Paris")


def main():
    setup_logging()
    log = logging.getLogger("automation")
    log.info("=" * 60)
    log.info("Gavio Automation — Demarrage")
    log.info("=" * 60)

    init_clients()

    scheduler = BackgroundScheduler(timezone=PARIS)

    # WF02 - Tracking auto (toutes les 4h)
    scheduler.add_job(
        wf02_tracking_auto.run,
        CronTrigger(hour="0,4,8,12,16,20", timezone=PARIS),
        id="wf02_tracking",
        name="Tracking auto CJ",
        misfire_grace_time=300,
    )

    # WF04 - Rapport quotidien (20h Paris)
    scheduler.add_job(
        wf04_daily_report.run,
        CronTrigger(hour=20, minute=0, timezone=PARIS),
        id="wf04_daily",
        name="Rapport quotidien",
        misfire_grace_time=600,
    )

    # WF05 - Blog SEO (Lun/Mer/Ven 06h)
    scheduler.add_job(
        wf05_blog_seo.run,
        CronTrigger(day_of_week="mon,wed,fri", hour=6, minute=0, timezone=PARIS),
        id="wf05_blog",
        name="Blog SEO",
        misfire_grace_time=900,
    )

    # WF06 - Synchro stock CJ (toutes les 4h, decale de WF02)
    scheduler.add_job(
        wf06_sync_stock_cj.run,
        CronTrigger(hour="2,6,10,14,18,22", timezone=PARIS),
        id="wf06_stock",
        name="Synchro stock CJ",
        misfire_grace_time=600,
    )

    # WF07 - Transmission commandes CJ (toutes les 15 min)
    scheduler.add_job(
        wf07_transmission_cj.run,
        CronTrigger(minute="*/15", timezone=PARIS),
        id="wf07_transmission",
        name="Transmission CJ",
        misfire_grace_time=120,
    )

    # WF08 - Nouveaux produits CJ (Dim 10h)
    scheduler.add_job(
        wf08_nouveaux_produits.run,
        CronTrigger(day_of_week="sun", hour=10, minute=0, timezone=PARIS),
        id="wf08_new_products",
        name="Nouveaux produits CJ",
        misfire_grace_time=900,
    )

    # WF10 - Meta social (FB + IG) - 12h
    scheduler.add_job(
        wf10_meta_social.run,
        CronTrigger(hour=12, minute=0, timezone=PARIS),
        id="wf10_meta",
        name="Meta FB+IG (12h)",
        misfire_grace_time=600,
    )

    # WF11 - TikTok - 13h + 20h
    scheduler.add_job(
        wf11_tiktok.run,
        CronTrigger(hour="13,20", minute=0, timezone=PARIS),
        id="wf11_tiktok",
        name="TikTok",
        misfire_grace_time=600,
    )

    # WF12 - Monitoring (toutes les 5 min)
    scheduler.add_job(
        wf12_monitoring.run,
        CronTrigger(minute="*/5", timezone=PARIS),
        id="wf12_monitor",
        name="Monitoring VPS",
        misfire_grace_time=60,
    )

    # WF13 - FAQ enrichment (Dim 11h)
    scheduler.add_job(
        wf13_faq_enrichment.run,
        CronTrigger(day_of_week="sun", hour=11, minute=0, timezone=PARIS),
        id="wf13_faq",
        name="FAQ enrichissement",
        misfire_grace_time=900,
    )

    # WF14 - Brevo email sequences (10h)
    scheduler.add_job(
        wf14_brevo_emails.run,
        CronTrigger(hour=10, minute=0, timezone=PARIS),
        id="wf14_brevo",
        name="Brevo sequences",
        misfire_grace_time=600,
    )

    # WF15 - Newsletter mensuelle (1er du mois 10h30)
    scheduler.add_job(
        wf15_newsletter.run,
        CronTrigger(day=1, hour=10, minute=30, timezone=PARIS),
        id="wf15_newsletter",
        name="Newsletter mensuelle",
        misfire_grace_time=3600,
    )

    # WF17 - SEO monitoring (Dim 8h)
    scheduler.add_job(
        wf17_seo_monitoring.run,
        CronTrigger(day_of_week="sun", hour=8, minute=0, timezone=PARIS),
        id="wf17_seo",
        name="SEO monitoring",
        misfire_grace_time=600,
    )

    # WF18 - Veille concurrence (Lun 7h)
    scheduler.add_job(
        wf18_concurrence.run,
        CronTrigger(day_of_week="mon", hour=7, minute=0, timezone=PARIS),
        id="wf18_concurrence",
        name="Veille concurrence",
        misfire_grace_time=600,
    )

    # WF21 - Google Shopping feed (5h)
    scheduler.add_job(
        wf21_google_shopping.run,
        CronTrigger(hour=5, minute=0, timezone=PARIS),
        id="wf21_shopping",
        name="Google Shopping feed",
        misfire_grace_time=600,
    )

    # WF22 - WP maintenance (Dim 4h)
    scheduler.add_job(
        wf22_wp_maintenance.run,
        CronTrigger(day_of_week="sun", hour=4, minute=0, timezone=PARIS),
        id="wf22_wp",
        name="WP maintenance",
        misfire_grace_time=900,
    )

    scheduler.start()
    jobs = scheduler.get_jobs()
    log.info("Scheduler demarre avec %d jobs :", len(jobs))
    for j in jobs:
        log.info("  - %s", j.name)

    # Flask webhook server (bloquant)
    log.info(
        "Serveur webhook sur %s:%s", Config.WEBHOOK_HOST, Config.WEBHOOK_PORT
    )
    log.info("Routes :")
    log.info("  POST /webhook/woocommerce/order   -> WF01")
    log.info("  POST /webhook/woocommerce/refund  -> WF03")
    log.info("  POST /webhook/stripe              -> Stripe events")
    log.info("  GET  /decision/<id>?action=...    -> Callbacks Telegram")
    log.info("  GET  /health                      -> Health check")
    log.info("=" * 60)

    app.run(host=Config.WEBHOOK_HOST, port=Config.WEBHOOK_PORT, debug=False)


if __name__ == "__main__":
    main()
