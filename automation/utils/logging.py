"""Logging configure pour le package automation Gavio."""
import logging
import sys
from pathlib import Path


def setup_logging(level=logging.INFO):
    """Configure le logging stdout + fichier."""
    if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    log_dir = Path(__file__).resolve().parent.parent.parent / "logs"
    log_dir.mkdir(exist_ok=True)

    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_dir / "automation.log", encoding="utf-8"),
        ],
    )
