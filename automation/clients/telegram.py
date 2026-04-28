"""Telegram Bot wrapper - bot Gavio."""
import logging
import requests

logger = logging.getLogger("automation.clients.telegram")


class TelegramClient:
    BASE_URL = "https://api.telegram.org"

    def __init__(self, bot_token: str, default_chat_id: str):
        self.bot_token = bot_token
        self.default_chat_id = default_chat_id
        self.session = requests.Session()

    def send_message(
        self,
        text: str,
        chat_id: str = None,
        parse_mode: str = "Markdown",
        inline_keyboard: list = None,
        disable_web_page_preview: bool = False,
    ) -> dict:
        """Envoie un message texte (Markdown par defaut), avec boutons optionnels."""
        payload = {
            "chat_id": chat_id or self.default_chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": disable_web_page_preview,
        }
        if inline_keyboard:
            payload["reply_markup"] = {"inline_keyboard": inline_keyboard}
        return self._post("sendMessage", payload)

    def send_photo(
        self,
        photo_url: str,
        caption: str = "",
        chat_id: str = None,
        parse_mode: str = "Markdown",
        inline_keyboard: list = None,
    ) -> dict:
        """Envoie une photo (URL ou file_id)."""
        payload = {
            "chat_id": chat_id or self.default_chat_id,
            "photo": photo_url,
            "caption": caption,
            "parse_mode": parse_mode,
        }
        if inline_keyboard:
            payload["reply_markup"] = {"inline_keyboard": inline_keyboard}
        return self._post("sendPhoto", payload)

    def edit_message_text(
        self,
        chat_id: str,
        message_id: int,
        text: str,
        parse_mode: str = "Markdown",
    ) -> dict:
        """Edite un message existant."""
        payload = {
            "chat_id": chat_id or self.default_chat_id,
            "message_id": message_id,
            "text": text,
            "parse_mode": parse_mode,
        }
        return self._post("editMessageText", payload)

    def _post(self, method: str, payload: dict) -> dict:
        url = f"{self.BASE_URL}/bot{self.bot_token}/{method}"
        try:
            resp = self.session.post(url, json=payload, timeout=30)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            # Si Markdown casse → retry sans parse_mode
            if "parse_mode" in payload and "400" in str(e):
                logger.warning(f"Markdown failed, retrying as plain text: {e}")
                payload.pop("parse_mode", None)
                try:
                    resp = self.session.post(url, json=payload, timeout=30)
                    resp.raise_for_status()
                    return resp.json()
                except requests.RequestException as e2:
                    logger.error(f"Telegram retry plain text failed: {e2}")
                    raise
            logger.error(f"Telegram API error ({method}): {e}")
            raise


# Helper functionnel pour les workflows : `from clients.telegram import notify`
_default_client: TelegramClient = None


def _get_client() -> TelegramClient:
    global _default_client
    if _default_client is None:
        from automation.config import Config
        _default_client = TelegramClient(
            Config.TELEGRAM_BOT_TOKEN, Config.TELEGRAM_CHAT_ID
        )
    return _default_client


def notify(text: str, **kwargs) -> dict:
    """Raccourci global : notify('Hello') sans avoir a instancier un client."""
    return _get_client().send_message(text, **kwargs)
