"""Flask web server - webhooks WooCommerce + Stripe + decision callbacks."""
import json
import logging
import threading

from flask import Flask, jsonify, redirect, request

from automation.config import Config
from automation.web.decision_store import DecisionStore

log = logging.getLogger("automation.web")

app = Flask(__name__)
decision_store = DecisionStore()


# --------------------------------------------------------------------- HEALTH
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "gavio-automation"}), 200


# --------------------------------------------------- WEBHOOK : COMMANDES (WF01)
@app.route("/webhook/woocommerce/order", methods=["POST"])
def webhook_order():
    """Recoit le webhook order.created de WooCommerce.

    WC peut envoyer JSON, form-encoded, ou raw body. On gere les 3.
    """
    order_data = request.get_json(silent=True)
    if not order_data:
        if request.form:
            order_data = request.form.to_dict()
        elif request.data:
            try:
                order_data = json.loads(request.data)
            except (json.JSONDecodeError, ValueError):
                order_data = {}

    if not order_data:
        log.warning(
            "Webhook payload vide. CT=%s", request.content_type
        )
        return jsonify({"status": "empty_payload"}), 200

    # Ping WC : payload contient juste webhook_id
    if "webhook_id" in order_data and "id" not in order_data:
        log.info("WC webhook ping (id=%s)", order_data.get("webhook_id"))
        return jsonify({"status": "pong"}), 200

    if "order" in order_data and isinstance(order_data["order"], dict):
        order_data = order_data["order"]

    log.info(
        "Webhook order : id=%s number=%s status=%s total=%s",
        order_data.get("id", "?"),
        order_data.get("number", "?"),
        order_data.get("status", "?"),
        order_data.get("total", "?"),
    )

    from automation.workflows.wf01_commande_auto import process_order
    threading.Thread(
        target=process_order,
        args=(order_data, decision_store),
        daemon=True,
    ).start()
    return jsonify({"status": "received"}), 200


# --------------------------------------------- WEBHOOK : REMBOURSEMENT (WF03)
@app.route("/webhook/woocommerce/refund", methods=["POST"])
def webhook_refund():
    data = request.get_json(silent=True) or {}
    log.info("Webhook refund : order=%s", data.get("order_id", "?"))
    from automation.workflows.wf03_remboursement import process_refund_request
    threading.Thread(
        target=process_refund_request,
        args=(data, decision_store),
        daemon=True,
    ).start()
    return jsonify({"status": "received"}), 200


# ------------------------------------------------------ STRIPE WEBHOOK (events)
@app.route("/webhook/stripe", methods=["POST"])
def webhook_stripe():
    """Receive Stripe events (payment_intent.succeeded, charge.refunded, etc).

    TODO : verifier la signature avec STRIPE_WEBHOOK_SECRET
    https://stripe.com/docs/webhooks/signatures
    """
    payload = request.get_json(silent=True) or {}
    event_type = payload.get("type", "?")
    log.info("Stripe webhook : %s", event_type)
    # TODO : router selon event_type
    #   - charge.refunded -> notif Telegram + maj WC status='refunded'
    #   - payment_intent.payment_failed -> notif
    return jsonify({"status": "received"}), 200


# ----------------------------------------------- DECISION CALLBACK (Telegram)
@app.route("/decision/<decision_id>", methods=["GET"])
def decision_callback(decision_id):
    """Callback URL appelee par les boutons inline Telegram."""
    action = request.args.get("action")
    if not action:
        return jsonify({"error": "action required"}), 400

    ok = decision_store.resolve(decision_id, action)
    if not ok:
        return (
            "<h2>Deja traitee</h2>"
            "<p>Cette decision a deja ete prise ou expiree.</p>",
            200,
        )

    # Page de confirmation (peut etre branding Apple-like)
    return (
        f"<!DOCTYPE html><html><head><meta charset='utf-8'>"
        f"<title>Gavio</title>"
        f"<style>body{{font-family:-apple-system,Helvetica,Arial,sans-serif;"
        f"background:#F5F5F7;color:#0A0A0A;display:flex;align-items:center;"
        f"justify-content:center;min-height:100vh;margin:0;}} "
        f".card{{background:#FFF;padding:48px 64px;border-radius:18px;"
        f"text-align:center;max-width:480px;}} h1{{margin:0 0 16px;font-size:28px;"
        f"font-weight:600;letter-spacing:-0.02em;}} p{{color:#86868B;}}</style>"
        f"</head><body><div class='card'>"
        f"<h1>✅ Action enregistree</h1>"
        f"<p>Decision : <strong>{action}</strong></p>"
        f"<p>Cette fenetre peut etre fermee.</p>"
        f"</div></body></html>",
        200,
    )
