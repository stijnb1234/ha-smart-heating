"""Thin HA glue: only urgent diagnoses (see engine/diagnosis.py) interrupt, as a persistent
notification and, when configured, a push to notify services (phones). Everything else is shown on
the dashboard and becomes advice when it recurs."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import TYPE_CHECKING

from .apply import call_service
from .const import DOMAIN
from .engine import Alert, AlertNotifier
from .engine.diagnosis import diagnose
from .i18n import tr
from .status import diagnosis_sentence

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


def _notification_id(alert: Alert) -> str:
    return f"{DOMAIN}_{alert.code}_{alert.room or 'system'}"


def notify_service(target: str) -> str:
    """`notify.mobile_app_phone` or `mobile_app_phone` -> `mobile_app_phone`."""
    return target.strip().removeprefix("notify.")


class AlertAdapter:
    def __init__(self, hass: HomeAssistant, lang: str = "en", notify_targets: Sequence[str] = ()) -> None:
        self._hass = hass
        self._lang = lang
        self._notifier = AlertNotifier()
        self._targets = tuple(t for t in (notify_service(t) for t in notify_targets) if t)

    async def async_apply(self, alerts: tuple[Alert, ...]) -> None:
        urgent = tuple(Alert(d.cause, d.room) for d in diagnose(alerts) if d.urgent)
        changes = self._notifier.update(urgent)
        for alert in changes.raised:
            message = diagnosis_sentence(alert.code, alert.room, self._lang)
            await self._call(
                "persistent_notification",
                "create",
                {"title": "Smart Heating", "message": message, "notification_id": _notification_id(alert)},
            )
            await self._push(message)
        for alert in changes.cleared:
            await self._call("persistent_notification", "dismiss", {"notification_id": _notification_id(alert)})
            text = diagnosis_sentence(alert.code, alert.room, self._lang)
            await self._push(tr(self._lang, "alert.resolved", text=text))

    async def _push(self, message: str) -> None:
        for target in self._targets:
            await self._call("notify", target, {"title": "Smart Heating", "message": message})

    async def _call(self, domain: str, service: str, data: dict) -> None:
        """One notification; a failing one must not keep the others from going out."""
        try:
            await call_service(self._hass, domain, service, data)
        except Exception:
            _LOGGER.warning("Sending a notification with %s.%s failed", domain, service, exc_info=True)
