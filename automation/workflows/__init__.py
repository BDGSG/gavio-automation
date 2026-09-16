"""Registry des clients API partages par tous les workflows."""
import logging
from typing import Optional

from automation.config import Config

logger = logging.getLogger("automation.workflows")

# Client globaux (lazy init via init_clients())
_cj = None
_wc = None
_telegram = None
_resend = None
_claude = None
_brevo = None
_kie = None


def init_clients():
    """Instancie tous les clients API partages."""
    global _cj, _wc, _telegram, _resend, _claude, _brevo, _kie

    from automation.clients.cj_dropshipping import CJClient
    from automation.clients.woocommerce import WooClient
    from automation.clients.telegram import TelegramClient
    from automation.clients.resend import ResendClient
    from automation.clients.claude import ClaudeClient
    from automation.clients.brevo import BrevoClient

    _cj = CJClient(Config.CJ_API_KEY, Config.CJ_BASE_URL)
    _wc = WooClient(
        Config.WC_URL,
        Config.WC_KEY,
        Config.WC_SECRET,
        wp_user=Config.WP_USER,
        wp_app_password=Config.WP_APP_PASSWORD,
    )
    _telegram = TelegramClient(Config.TELEGRAM_BOT_TOKEN, Config.TELEGRAM_CHAT_ID)
    _resend = ResendClient(
        Config.RESEND_API_KEY, Config.RESEND_FROM_EMAIL, Config.RESEND_FROM_NAME
    )

    # Kie.ai en fallback Claude
    if Config.KIE_API_KEY:
        try:
            # Si pas dispo on continue (Kie est optionnel)
            from automation.clients.claude import ClaudeClient as _C  # noqa
            _kie = _build_kie_fallback()
        except Exception as e:
            logger.warning("Kie fallback init failed: %s", e)
            _kie = None

    if Config.ANTHROPIC_API_KEY:
        _claude = ClaudeClient(
            Config.ANTHROPIC_API_KEY,
            default_model=Config.ANTHROPIC_MODEL,
            fallback=_kie,
        )

    if Config.BREVO_API_KEY:
        _brevo = BrevoClient(
            Config.BREVO_API_KEY,
            Config.BREVO_SENDER_EMAIL,
            Config.BREVO_SENDER_NAME,
        )

    logger.info("Clients initialises : cj=%s, wc=%s, claude=%s, brevo=%s",
                bool(_cj), bool(_wc), bool(_claude), bool(_brevo))


def _build_kie_fallback():
    """Stub minimal Kie.ai (text gen). A enrichir si besoin."""
    import requests

    class _KieMin:
        def __init__(self, api_key: str):
            self.api_key = api_key
            self.session = requests.Session()
            self.session.headers["Authorization"] = f"Bearer {api_key}"

        def generate(self, system: str, user: str, max_tokens: int = 4096) -> str:
            url = "https://api.kie.ai/api/v1/chat/completions"
            payload = {
                "model": "claude-sonnet-4-5-20250929",
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "max_tokens": max_tokens,
            }
            r = self.session.post(url, json=payload, timeout=60)
            r.raise_for_status()
            data = r.json()
            if "choices" not in data:
                raise RuntimeError(f"Reponse Kie.ai inattendue : {data}")
            return data["choices"][0]["message"]["content"]

    return _KieMin(Config.KIE_API_KEY)


# ----------------------------------------------------------------- ACCESSORS
def get_cj():
    return _cj

def get_wc():
    return _wc

def get_telegram():
    return _telegram

def get_resend():
    return _resend

def get_claude():
    return _claude

def get_brevo():
    return _brevo

def get_kie():
    return _kie
