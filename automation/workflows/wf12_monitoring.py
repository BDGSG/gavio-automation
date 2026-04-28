"""WF12 — Monitoring VPS.

Cron toutes les 5 min.
Surveille CPU, RAM, disque. Alerte Telegram si seuils depasses
(rate-limited a 1 alerte / 15 min).
"""
import logging
import time
from datetime import datetime
from zoneinfo import ZoneInfo

import psutil

from automation.config import Config
from automation.utils.error_handling import workflow_handler
from automation.workflows import get_telegram

log = logging.getLogger("automation.wf12")
PARIS = ZoneInfo("Europe/Paris")

_last_alert = {}
ALERT_COOLDOWN = 15 * 60  # 15 min


def _should_alert(metric: str) -> bool:
    now = datetime.now(PARIS)
    last = _last_alert.get(metric)
    if last and (now - last).total_seconds() < ALERT_COOLDOWN:
        return False
    _last_alert[metric] = now
    return True


@workflow_handler("wf12_monitoring")
def run():
    tg = get_telegram()
    now = datetime.now(PARIS).strftime("%d/%m/%Y %H:%M")

    # CPU : 3 mesures de 5s pour eviter les pics
    samples = []
    for _ in range(3):
        samples.append(psutil.cpu_percent(interval=5))
    cpu = round(sum(samples) / len(samples), 1)

    mem = psutil.virtual_memory()
    ram = mem.percent
    ram_used = mem.used / (1024 ** 3)
    ram_total = mem.total / (1024 ** 3)

    disk = psutil.disk_usage("/")
    disk_pct = disk.percent
    disk_used = disk.used / (1024 ** 3)
    disk_total = disk.total / (1024 ** 3)

    log.info(
        "VPS : CPU=%s%% | RAM=%s%% (%.1f/%.1f GB) | Disk=%s%% (%.1f/%.1f GB)",
        cpu, ram, ram_used, ram_total, disk_pct, disk_used, disk_total,
    )

    alerts = []
    if cpu >= Config.MONITOR_CPU_THRESHOLD:
        alerts.append(f"CPU : *{cpu}%* (seuil {Config.MONITOR_CPU_THRESHOLD}%)")
        # Top processes
        for p in psutil.process_iter(["name", "cpu_percent"]):
            pass
        time.sleep(2)
        top = sorted(
            psutil.process_iter(["name", "cpu_percent"]),
            key=lambda p: p.info["cpu_percent"] or 0,
            reverse=True,
        )[:5]
        lines = [
            f"  - {p.info['name']}: {p.info['cpu_percent']}%"
            for p in top if (p.info["cpu_percent"] or 0) > 0
        ]
        if lines:
            alerts.append("Top :\n" + "\n".join(lines))

    if ram >= Config.MONITOR_RAM_THRESHOLD:
        alerts.append(
            f"RAM : *{ram}%* ({ram_used:.1f}/{ram_total:.1f} GB, "
            f"seuil {Config.MONITOR_RAM_THRESHOLD}%)"
        )
    if disk_pct >= Config.MONITOR_DISK_THRESHOLD:
        alerts.append(
            f"Disque : *{disk_pct}%* ({disk_used:.1f}/{disk_total:.1f} GB, "
            f"seuil {Config.MONITOR_DISK_THRESHOLD}%)"
        )

    if alerts and _should_alert("system"):
        msg = (
            f"\U0001f6a8 *ALERTE VPS — Gavio*\n{now}\n\n"
            + "\n\n".join(alerts)
            + "\n\n_Verifier les processus / redemarrer le service lourd._"
        )
        tg.send_message(msg)
        log.warning("Alert sent: %d threshold(s)", len(alerts))
    return {"status": "ok", "cpu": cpu, "ram": ram, "disk": disk_pct}
