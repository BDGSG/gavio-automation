"""Resend API client - emails transactionnels."""
import logging
from typing import Optional

import requests

logger = logging.getLogger("automation.clients.resend")

RESEND_API = "https://api.resend.com"


class ResendClient:
    def __init__(self, api_key: str, from_email: str, from_name: str = "Gavio"):
        self.api_key = api_key
        self.from_email = from_email
        self.from_name = from_name
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        })

    def send_email(
        self,
        to: str | list,
        subject: str,
        html: str,
        text: Optional[str] = None,
        reply_to: Optional[str] = None,
        tags: Optional[list] = None,
    ) -> dict:
        """Envoi un email HTML transactionnel.

        Args:
            to: email destinataire (str) ou liste d'emails
            subject: objet
            html: contenu HTML
            text: version texte (optionnel)
            reply_to: adresse de reponse
            tags: liste [{name, value}] pour tracking
        """
        recipients = [to] if isinstance(to, str) else to
        payload = {
            "from": f"{self.from_name} <{self.from_email}>",
            "to": recipients,
            "subject": subject,
            "html": html,
        }
        if text:
            payload["text"] = text
        if reply_to:
            payload["reply_to"] = reply_to
        if tags:
            payload["tags"] = tags

        try:
            r = self.session.post(
                f"{RESEND_API}/emails", json=payload, timeout=20
            )
            r.raise_for_status()
            data = r.json()
            logger.info("Resend OK -> %s : %s (id=%s)", recipients, subject, data.get("id"))
            return data
        except requests.RequestException as e:
            logger.error("Resend error: %s", e)
            raise

    def send_template(
        self,
        to: str,
        subject: str,
        title: str,
        body_html: str,
        cta_label: Optional[str] = None,
        cta_url: Optional[str] = None,
        footer: Optional[str] = None,
    ) -> dict:
        """Envoi un email avec template Apple-like (cohese avec branding Gavio)."""
        cta_html = ""
        if cta_label and cta_url:
            cta_html = (
                f'<div style="text-align:center;margin:32px 0;">'
                f'<a href="{cta_url}" style="background:#0A0A0A;color:#FFFFFF;'
                f'padding:14px 32px;border-radius:980px;text-decoration:none;'
                f'font-weight:500;font-size:15px;display:inline-block;">'
                f'{cta_label}</a></div>'
            )
        if footer is None:
            footer = (
                "Gavio &middot; Le futur, sans superflu.<br>"
                "<a href='https://gavio.fr' style='color:#86868B;'>gavio.fr</a>"
            )

        html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;background:#F5F5F7;font-family:-apple-system,'SF Pro Display',Helvetica,Arial,sans-serif;">
<table role="presentation" width="100%" style="background:#F5F5F7;">
  <tr><td align="center" style="padding:48px 16px;">
    <table role="presentation" width="600" style="background:#FFFFFF;border-radius:18px;overflow:hidden;">
      <tr><td style="padding:48px 48px 16px;">
        <h1 style="margin:0 0 16px;font-size:32px;font-weight:600;color:#0A0A0A;letter-spacing:-0.02em;">{title}</h1>
        <div style="font-size:17px;line-height:1.5;color:#1D1D1F;">{body_html}</div>
        {cta_html}
      </td></tr>
      <tr><td style="padding:24px 48px 40px;border-top:1px solid #E5E5EA;text-align:center;font-size:13px;color:#86868B;">
        {footer}
      </td></tr>
    </table>
  </td></tr>
</table>
</body></html>"""

        return self.send_email(to, subject, html)
