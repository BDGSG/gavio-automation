"""Routes Stripe - actuellement integrees dans web/app.py.

Endpoint : /webhook/stripe

TODO : extraire ici la logique Stripe complete :
  - Verification signature avec STRIPE_WEBHOOK_SECRET
  - Routing par event_type :
      * charge.refunded
      * payment_intent.succeeded
      * payment_intent.payment_failed
      * charge.dispute.created  (litiges -> alerte urgente)
"""
