"""Thin HA glue: keeps Home Assistant Repairs in step with the advice, and carries out Apply,
Snooze and Undo. Detection and the changes themselves are pure (engine/advice.py, advice_actions.py).
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import issue_registry as ir
from homeassistant.util import dt as dt_util

from .advice_actions import AdviceState, advice_text, advice_title, apply_advice, undo_advice
from .const import CONF_ROOMS, DOMAIN
from .engine.advice import Advice, detect

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

    from .advice_store import AdviceStore
    from .controller import Controller

_LOGGER = logging.getLogger(__name__)
ISSUE_PREFIX = "advice_"
REFRESH_EVERY = timedelta(hours=1)
SAVE_EVERY = timedelta(minutes=15)


class Advisor:
    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        shared: dict,
        controller: Controller,
        store: AdviceStore,
        state: AdviceState,
        trv_rooms: Sequence[str],
    ) -> None:
        self._hass, self._entry, self._shared = hass, entry, shared
        self._controller, self._store = controller, store
        self.state = state
        self._trv_rooms = frozenset(trv_rooms)
        self.current: list[Advice] = []
        self._refreshed: datetime | None = None
        self._saved = dt_util.utcnow()

    def names(self) -> dict[str, str]:
        """Friendly names of the entities an advice may suggest as occupants."""
        return {
            p: state.name
            for a in self.current
            for p in a.people
            if (state := self._hass.states.get(p)) is not None
        }

    async def async_tick(self) -> None:
        """Every control cycle: refresh the advice hourly, save the evidence now and then."""
        now = dt_util.utcnow()
        if self._refreshed is None or now - self._refreshed >= REFRESH_EVERY:
            await self.async_refresh()
        if now - self._saved >= SAVE_EVERY:
            await self.async_save()

    async def async_save(self) -> None:
        await self._store.async_save(self._controller.advice_log, self.state)
        self._saved = dt_util.utcnow()

    async def async_refresh(self) -> None:
        now = dt_util.now()
        self._refreshed = dt_util.utcnow()
        self.state.prune(now)
        rooms = self._shared["rooms"]
        found = detect(
            self._controller.advice_log,
            rooms,
            now,
            sensorless=self._trv_rooms - set(self._shared["sensor_entities"]),
            without_occupants={r.name for r in rooms} - set(self._shared["presence_entities"]),
            suggestions=self._controller.suggestions(now),
        )
        self.current = self.state.visible(found, now)
        self._sync_issues()

    def _sync_issues(self) -> None:
        wanted = {ISSUE_PREFIX + a.key: a for a in self.current}
        registry = ir.async_get(self._hass)
        for (domain, issue_id), issue in list(registry.issues.items()):
            # An ignored (dismissed) issue stays, or it would come back as new.
            if (
                domain == DOMAIN
                and issue_id.startswith(ISSUE_PREFIX)
                and issue_id not in wanted
                and issue.dismissed_version is None
            ):
                ir.async_delete_issue(self._hass, DOMAIN, issue_id)
        lang, names = self._shared["lang"], self.names()
        for issue_id, advice in wanted.items():
            ir.async_create_issue(
                self._hass,
                DOMAIN,
                issue_id,
                is_fixable=True,
                is_persistent=False,
                severity=ir.IssueSeverity.WARNING,
                translation_key="advice_apply" if advice.applicable else "advice",
                translation_placeholders={
                    "title": advice_title(advice, lang),
                    "text": advice_text(advice, lang, self.state.cost_per_hour, names, self.state.currency),
                },
                data={"entry_id": self._entry.entry_id, "key": advice.key},
            )

    def find(self, key: str) -> Advice | None:
        return next((a for a in self.current if a.key == key), None)

    async def async_snooze(self, key: str) -> None:
        self.state.hide(key, dt_util.now())
        await self.async_save()
        await self.async_refresh()

    async def async_apply(self, key: str, people: Sequence[str] = ()) -> None:
        advice = self.find(key)
        if advice is None:
            raise ServiceValidationError(translation_domain=DOMAIN, translation_key="advice_gone")
        options = self._entry.options
        try:
            rooms, before = apply_advice(
                options.get(CONF_ROOMS, []), advice, duration=self._shared["boost_duration"], people=people
            )
        except ValueError as err:
            raise ServiceValidationError(translation_domain=DOMAIN, translation_key="advice_gone") from err
        now = dt_util.now()
        today = now.date()
        self.state.applied.append(
            {
                "at": now.isoformat(),
                "key": key,
                "room": advice.room,
                "room_id": next(r["id"] for r in rooms if r["name"] == advice.room),
                "before": before,
                "hours_before": self._controller.advice_log.hours_per_week(
                    advice.room, "sole", today - timedelta(days=7), today
                ),
            }
        )
        # Not again while the evidence still shows the old settings.
        self.state.hide(key, now)
        await self.async_save()
        _LOGGER.info("Applying advice %s", key)
        # Changing the options reloads the integration with the new settings.
        self._hass.config_entries.async_update_entry(self._entry, options={**options, CONF_ROOMS: rooms})

    async def async_undo(self) -> None:
        """Put back the settings changed by the most recently applied advice."""
        self.state.prune(dt_util.now())
        if not self.state.applied:
            raise ServiceValidationError(translation_domain=DOMAIN, translation_key="nothing_to_undo")
        record = self.state.applied.pop()
        # Undone on purpose: do not propose it again right away.
        self.state.hide(record["key"], dt_util.now())
        await self.async_save()
        options = self._entry.options
        rooms = undo_advice(options.get(CONF_ROOMS, []), record)
        self._hass.config_entries.async_update_entry(self._entry, options={**options, CONF_ROOMS: rooms})
