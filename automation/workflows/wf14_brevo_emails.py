"""WF14 — Brevo email sequences.

Cron : 10h Paris quotidien.
Gere 4 sequences :
  - Welcome (nouveau client : J+0, J+1, J+3)
  - Abandon panier (J+1, J+3, J+7)
  - Post-achat (J+3 confirmation, J+10 satisfaction, J+30 cross-sell)
  - Retention (J+60 inactif, J+90 win-back avec promo)

TODO :
- Configurer BREVO_API_KEY (TODO utilisateur)
- Creer les 4 listes Brevo + 12 templates HTML
- Logic : iterer sur clients, calculer la sequence en fonction des dates,
  envoyer le bon template via brevo.send_transactional
"""
import logging
from automation.utils.error_handling import workflow_handler
from automation.workflows import get_brevo, get_telegram

log = logging.getLogger("automation.wf14")


@workflow_handler("wf14_brevo_emails")
def run():
    brevo = get_brevo()
    tg = get_telegram()

    if not brevo:
        log.info("WF14 desactive : BREVO_API_KEY non configure")
        return {"status": "skipped", "reason": "no_brevo_key"}

    # PSEUDO-CODE :
    # for customer in wc.get_customers(after=last_run):
    #     orders = wc.get_orders(customer=customer.id)
    #     last_order = orders[-1] if orders else None
    #     # Welcome series
    #     days_since_signup = (now - customer.created).days
    #     if days_since_signup in (0, 1, 3):
    #         brevo.send_transactional(customer.email, name, subject, html_for_day(d))
    #     # Abandoned cart
    #     # ... etc
    #
    # for order in wc.get_orders(status='completed', after=last_run):
    #     days_since_completed = (now - order.completed_at).days
    #     if days_since_completed in (3, 10, 30):
    #         brevo.send_transactional(...)

    log.info("WF14 Brevo : a implementer")
    return {"status": "skipped", "reason": "skeleton"}
