"""WF22 — WordPress maintenance.

Cron : Dim 04h Paris.
Connection SSH au serveur de prod, execute :
  - wp core check-update / update
  - wp plugin update --all
  - wp theme update --all
  - cache flush
Envoie un rapport Telegram.

NOTE : WordPress Gavio sera probablement heberge sur un autre VPS / Coolify.
       Configure SSH_HOST/USER/PASS/WP_PATH dans .env si tu veux activer ce WF.
"""
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from automation.config import Config
from automation.utils.error_handling import workflow_handler
from automation.workflows import get_telegram

log = logging.getLogger("automation.wf22")
PARIS = ZoneInfo("Europe/Paris")


def _ssh_exec(ssh, cmd: str, timeout: int = 60) -> str:
    _, stdout, _ = ssh.exec_command(cmd, timeout=timeout)
    return stdout.read().decode("utf-8", "replace").strip()


def _connect():
    import paramiko
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(
        Config.SSH_HOST,
        port=Config.SSH_PORT,
        username=Config.SSH_USER,
        password=Config.SSH_PASS,
        timeout=15,
    )
    return ssh


@workflow_handler("wf22_wp_maintenance")
def run():
    tg = get_telegram()
    now = datetime.now(tz=PARIS)

    if not (Config.SSH_HOST and Config.SSH_USER and Config.WP_PATH):
        log.info("WF22 desactive : SSH_HOST/USER/WP_PATH non configures")
        return {"status": "skipped", "reason": "no_ssh_config"}

    lines = [f"\U0001f527 *Maintenance WordPress Gavio — {now.strftime('%d/%m/%Y')}*\n"]

    try:
        ssh = _connect()
    except Exception as e:
        log.error("SSH failed: %s", e)
        tg.send_message(f"❌ WF22 : connexion SSH echouee\n{e}")
        return {"status": "error"}

    try:
        wp_path = Config.WP_PATH
        # 1. Core
        ver = _ssh_exec(ssh, f"wp core version --path={wp_path}")
        check = _ssh_exec(ssh, f"wp core check-update --format=csv --path={wp_path}")
        if "version" in check and "Success" not in check:
            _ssh_exec(ssh, f"wp core update --path={wp_path}", timeout=120)
            new_ver = _ssh_exec(ssh, f"wp core version --path={wp_path}")
            lines.append(f"⬆️ *WordPress* : {ver} → {new_ver}")
            _ssh_exec(ssh, f"wp core update-db --path={wp_path}")
        else:
            lines.append(f"✅ *WordPress* : {ver} (a jour)")

        # 2. Plugins
        plugins = _ssh_exec(
            ssh, f"wp plugin list --update=available --format=csv --path={wp_path}"
        )
        if plugins and "name" in plugins:
            count = len([l for l in plugins.split("\n") if l and "name" not in l])
            if count > 0:
                _ssh_exec(ssh, f"wp plugin update --all --path={wp_path}", timeout=180)
                lines.append(f"\n⬆️ *{count} plugins* mis a jour")
            else:
                lines.append("\n✅ *Plugins* : a jour")
        else:
            lines.append("\n✅ *Plugins* : a jour")

        # 3. Themes
        themes = _ssh_exec(
            ssh, f"wp theme list --update=available --format=csv --path={wp_path}"
        )
        if themes and "name" in themes:
            count = len([l for l in themes.split("\n") if l and "name" not in l])
            if count > 0:
                _ssh_exec(ssh, f"wp theme update --all --path={wp_path}", timeout=120)
                lines.append(f"\n⬆️ *Themes* : {count} mis a jour")
            else:
                lines.append("\n✅ *Themes* : a jour")
        else:
            lines.append("\n✅ *Themes* : a jour")

        # 4. Cache
        _ssh_exec(ssh, f"wp cache flush --path={wp_path}")
        lines.append("\n\U0001f9f9 Cache purge")

        # 5. Health
        url = _ssh_exec(ssh, f"wp option get siteurl --path={wp_path}")
        lines.append(f"\n\U0001f310 {url}")

    except Exception as e:
        lines.append(f"\n❌ Erreur : {str(e)[:200]}")
        log.error("Maintenance error: %s", e)
    finally:
        try:
            ssh.close()
        except Exception:
            pass

    tg.send_message("\n".join(lines))
    return {"status": "ok"}
