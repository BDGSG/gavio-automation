"""In-memory store pour les decisions Telegram en attente.

Permet le pattern "envoie un message avec boutons -> attend la decision -> callback".
Utilise par WF01 (24h timeout) et WF03 (48h timeout).
"""
import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Optional

log = logging.getLogger("automation.web.decision_store")


@dataclass
class PendingDecision:
    decision_id: str
    created_at: float
    timeout_seconds: float
    context: dict
    callback: Callable
    action: Optional[str] = None
    resolved: bool = False
    event: threading.Event = field(default_factory=threading.Event)


class DecisionStore:
    def __init__(self):
        self._decisions: dict[str, PendingDecision] = {}
        self._lock = threading.Lock()
        self._cleanup = threading.Thread(target=self._cleanup_loop, daemon=True)
        self._cleanup.start()

    def create(
        self,
        decision_id: str,
        context: dict,
        callback: Callable,
        timeout_seconds: float = 86400,
    ) -> PendingDecision:
        d = PendingDecision(
            decision_id=decision_id,
            created_at=time.time(),
            timeout_seconds=timeout_seconds,
            context=context,
            callback=callback,
        )
        with self._lock:
            self._decisions[decision_id] = d
        log.info("Decision %s created (timeout %ss)", decision_id, timeout_seconds)
        return d

    def resolve(self, decision_id: str, action: str) -> bool:
        with self._lock:
            d = self._decisions.get(decision_id)
            if not d or d.resolved:
                return False
            d.action = action
            d.resolved = True
            d.event.set()

        log.info("Decision %s resolved: %s", decision_id, action)
        threading.Thread(
            target=d.callback, args=(action, d.context), daemon=True
        ).start()
        return True

    def _cleanup_loop(self):
        while True:
            time.sleep(60)
            now = time.time()
            expired = []
            with self._lock:
                for did, d in list(self._decisions.items()):
                    if not d.resolved and (now - d.created_at) > d.timeout_seconds:
                        expired.append(d)
                    elif d.resolved and (now - d.created_at) > 3600:
                        del self._decisions[did]
            for d in expired:
                log.info("Decision %s timeout", d.decision_id)
                self.resolve(d.decision_id, "timeout")
