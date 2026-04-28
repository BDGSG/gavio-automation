"""Brevo (ex-Sendinblue) - email marketing automation : newsletter, sequences."""
import logging
from typing import Optional

import requests

logger = logging.getLogger("automation.clients.brevo")
BREVO_API = "https://api.brevo.com/v3"


class BrevoClient:
    def __init__(self, api_key: str, sender_email: str, sender_name: str):
        self.api_key = api_key
        self.sender_email = sender_email
        self.sender_name = sender_name
        self.session = requests.Session()
        self.session.headers.update({
            "api-key": api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        })

    def send_transactional(
        self,
        to_email: str,
        to_name: str,
        subject: str,
        html_content: str,
        reply_to: Optional[str] = None,
        tags: Optional[list] = None,
    ) -> dict:
        payload = {
            "sender": {"name": self.sender_name, "email": self.sender_email},
            "to": [{"email": to_email, "name": to_name}],
            "subject": subject,
            "htmlContent": html_content,
        }
        if reply_to:
            payload["replyTo"] = {"email": reply_to}
        if tags:
            payload["tags"] = tags

        r = self.session.post(f"{BREVO_API}/smtp/email", json=payload, timeout=15)
        if r.status_code in (200, 201):
            logger.info("Brevo email -> %s : %s", to_email, subject)
            return r.json()
        logger.error("Brevo error %s: %s", r.status_code, r.text[:200])
        return {}

    def create_contact(
        self, email: str, attributes: dict = None, list_ids: list = None
    ) -> bool:
        payload = {"email": email, "updateEnabled": True}
        if attributes:
            payload["attributes"] = attributes
        if list_ids:
            payload["listIds"] = list_ids

        r = self.session.post(f"{BREVO_API}/contacts", json=payload, timeout=15)
        ok = r.status_code in (200, 201, 204)
        if ok:
            logger.info("Brevo contact upsert : %s", email)
        else:
            logger.error("Brevo contact error %s: %s", r.status_code, r.text[:200])
        return ok

    def get_lists(self) -> list:
        r = self.session.get(f"{BREVO_API}/contacts/lists", timeout=15)
        if r.status_code == 200:
            return r.json().get("lists", [])
        return []

    def create_list(self, name: str, folder_id: int = 1) -> int:
        r = self.session.post(
            f"{BREVO_API}/contacts/lists",
            json={"name": name, "folderId": folder_id},
            timeout=15,
        )
        if r.status_code in (200, 201):
            return r.json().get("id", 0)
        logger.error("Brevo create_list error: %s %s", r.status_code, r.text[:200])
        return 0

    def send_campaign(
        self,
        name: str,
        subject: str,
        html_content: str,
        list_ids: list,
        scheduled_at: Optional[str] = None,
        tags: Optional[list] = None,
    ) -> dict:
        payload = {
            "name": name,
            "subject": subject,
            "sender": {"name": self.sender_name, "email": self.sender_email},
            "type": "classic",
            "htmlContent": html_content,
            "recipients": {"listIds": list_ids},
        }
        if scheduled_at:
            payload["scheduledAt"] = scheduled_at
        if tags:
            payload["tag"] = ",".join(tags)

        r = self.session.post(f"{BREVO_API}/emailCampaigns", json=payload, timeout=15)
        if r.status_code in (200, 201):
            return r.json()
        logger.error("Brevo campaign error %s: %s", r.status_code, r.text[:200])
        return {}

    def send_campaign_now(self, campaign_id: int) -> bool:
        r = self.session.post(
            f"{BREVO_API}/emailCampaigns/{campaign_id}/sendNow", timeout=15
        )
        return r.status_code in (200, 201, 204)
