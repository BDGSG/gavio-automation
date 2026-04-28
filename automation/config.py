"""Gavio Automation - Configuration centralisee.

Charge les variables d'environnement depuis .env (local) ou directement depuis
les env vars Coolify (prod).
"""
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    _env_path = Path(__file__).resolve().parent.parent / ".env"
    if _env_path.exists():
        load_dotenv(_env_path)
except ImportError:
    pass


class Config:
    # ----------------------------------------------------------------------
    # WooCommerce / WordPress (Gavio)
    # ----------------------------------------------------------------------
    WC_URL: str = os.getenv("WC_URL", "https://gavio.fr")
    WC_KEY: str = os.getenv("WC_KEY", "")  # Consumer Key
    WC_SECRET: str = os.getenv("WC_SECRET", "")  # Consumer Secret

    # WordPress admin (pour publication blog)
    WP_USER: str = os.getenv("WP_USER", "")
    WP_APP_PASSWORD: str = os.getenv("WP_APP_PASSWORD", "")

    # ----------------------------------------------------------------------
    # CJ Dropshipping
    # ----------------------------------------------------------------------
    CJ_API_KEY: str = os.getenv(
        "CJ_API_KEY",
        "CJ3934481@api@dc4b7fab646f4e6c9876d2486266f4bf",
    )
    CJ_BASE_URL: str = os.getenv("CJ_BASE_URL", "https://developers.cjdropshipping.com")

    # ----------------------------------------------------------------------
    # Telegram (Bot Gavio)
    # ----------------------------------------------------------------------
    TELEGRAM_BOT_TOKEN: str = os.getenv(
        "TELEGRAM_BOT_TOKEN",
        "8546540157:AAFBkRmkKU45clBLt9O6HB0jNMHRCfLpAPo",
    )
    TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "7445971784")

    # ----------------------------------------------------------------------
    # Email transactionnel (Resend)
    # ----------------------------------------------------------------------
    RESEND_API_KEY: str = os.getenv(
        "RESEND_API_KEY",
        "re_RXcHaNcA_PyE37EPqE1nYK8deVmxs6ktu",
    )
    RESEND_FROM_EMAIL: str = os.getenv("RESEND_FROM_EMAIL", "commandes@gavio.fr")
    RESEND_FROM_NAME: str = os.getenv("RESEND_FROM_NAME", "Gavio")

    # ----------------------------------------------------------------------
    # Anthropic (Claude pour blog SEO, FAQ, descriptions produits)
    # ----------------------------------------------------------------------
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    ANTHROPIC_MODEL: str = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5-20250929")

    # ----------------------------------------------------------------------
    # Kie.ai (fallback LLM + generation images FLUX + videos Seedance)
    # ----------------------------------------------------------------------
    KIE_API_KEY: str = os.getenv("KIE_API_KEY", "2c44ed8970990c113f4dcf4742018516")

    # ----------------------------------------------------------------------
    # Brevo (email marketing - sequences, newsletter)
    # ----------------------------------------------------------------------
    BREVO_API_KEY: str = os.getenv("BREVO_API_KEY", "")  # TODO utilisateur fournit
    BREVO_SENDER_EMAIL: str = os.getenv("BREVO_SENDER_EMAIL", "newsletter@gavio.fr")
    BREVO_SENDER_NAME: str = os.getenv("BREVO_SENDER_NAME", "Gavio")

    # ----------------------------------------------------------------------
    # Stripe (remboursements + webhook)
    # ----------------------------------------------------------------------
    STRIPE_SECRET_KEY: str = os.getenv("STRIPE_SECRET_KEY", "")
    STRIPE_WEBHOOK_SECRET: str = os.getenv("STRIPE_WEBHOOK_SECRET", "")

    # ----------------------------------------------------------------------
    # Google Sheets (logs commandes / blog / monitoring)
    # ----------------------------------------------------------------------
    GOOGLE_SHEETS_CREDENTIALS_FILE: str = os.getenv(
        "GOOGLE_SHEETS_CREDENTIALS_FILE", "credentials.json"
    )
    GOOGLE_SHEETS_DOCUMENT_ID: str = os.getenv("GOOGLE_SHEETS_DOCUMENT_ID", "")

    # ----------------------------------------------------------------------
    # Social Media
    # ----------------------------------------------------------------------
    META_PAGE_ACCESS_TOKEN: str = os.getenv("META_PAGE_ACCESS_TOKEN", "")
    META_PAGE_ID: str = os.getenv("META_PAGE_ID", "")
    META_IG_USER_ID: str = os.getenv("META_IG_USER_ID", "")

    TIKTOK_ACCESS_TOKEN: str = os.getenv("TIKTOK_ACCESS_TOKEN", "")
    AYRSHARE_API_KEY: str = os.getenv("AYRSHARE_API_KEY", "")

    # ----------------------------------------------------------------------
    # SEO Tools
    # ----------------------------------------------------------------------
    DATAFORSEO_LOGIN: str = os.getenv("DATAFORSEO_LOGIN", "")
    DATAFORSEO_PASSWORD: str = os.getenv("DATAFORSEO_PASSWORD", "")

    # ----------------------------------------------------------------------
    # SSH (pour WP maintenance)
    # ----------------------------------------------------------------------
    SSH_HOST: str = os.getenv("SSH_HOST", "")
    SSH_PORT: int = int(os.getenv("SSH_PORT", "22"))
    SSH_USER: str = os.getenv("SSH_USER", "")
    SSH_PASS: str = os.getenv("SSH_PASS", "")
    WP_PATH: str = os.getenv("WP_PATH", "")

    # ----------------------------------------------------------------------
    # Webhook server
    # ----------------------------------------------------------------------
    WEBHOOK_HOST: str = os.getenv("WEBHOOK_HOST", "0.0.0.0")
    WEBHOOK_PORT: int = int(os.getenv("WEBHOOK_PORT", "5000"))
    WEBHOOK_BASE_URL: str = os.getenv(
        "WEBHOOK_BASE_URL", "http://localhost:5000"
    )

    # ----------------------------------------------------------------------
    # Anti-fraude
    # ----------------------------------------------------------------------
    FRAUD_MAX_AMOUNT: float = float(os.getenv("FRAUD_MAX_AMOUNT", "2500"))
    FRAUD_ALLOWED_COUNTRIES: list = os.getenv(
        "FRAUD_ALLOWED_COUNTRIES",
        "FR,BE,LU,CH,MC,DE,IT,ES,NL,PT,AT,IE",
    ).split(",")

    # ----------------------------------------------------------------------
    # Monitoring (WF12)
    # ----------------------------------------------------------------------
    MONITOR_CPU_THRESHOLD: int = int(os.getenv("MONITOR_CPU_THRESHOLD", "80"))
    MONITOR_RAM_THRESHOLD: int = int(os.getenv("MONITOR_RAM_THRESHOLD", "85"))
    MONITOR_DISK_THRESHOLD: int = int(os.getenv("MONITOR_DISK_THRESHOLD", "90"))

    # ----------------------------------------------------------------------
    # Branding
    # ----------------------------------------------------------------------
    BRAND_NAME: str = "Gavio"
    BRAND_TAGLINE: str = "Le futur, sans superflu."
    BRAND_DOMAIN: str = "gavio.fr"
