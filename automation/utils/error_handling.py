"""Decorateur d'erreur pour les workflows : log + Telegram alert."""
import functools
import logging
import traceback
from datetime import datetime


def workflow_handler(workflow_name: str):
    """Decorateur : capture les exceptions et envoie une alerte Telegram."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            logger = logging.getLogger(f"automation.{workflow_name}")
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_msg = (
                    f"*ERREUR Workflow {workflow_name}*\n\n"
                    f"Erreur : {str(e)[:300]}\n"
                    f"Date : {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n"
                    f"```\n{traceback.format_exc()[-500:]}\n```"
                )
                logger.error(f"Workflow {workflow_name} failed: {e}", exc_info=True)
                try:
                    from automation.workflows import get_telegram
                    tg = get_telegram()
                    if tg:
                        tg.send_message(error_msg)
                except Exception:
                    logger.critical(
                        "Failed to send error notification to Telegram"
                    )
        return wrapper
    return decorator
