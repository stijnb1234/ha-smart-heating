"""Thin HA glue: the Repairs fix dialog of an advice: apply it, or snooze it."""

from __future__ import annotations

import voluptuous as vol
from homeassistant.components.repairs import RepairsFlow
from homeassistant.core import HomeAssistant
from homeassistant.helpers import selector

from .const import DOMAIN


class AdviceFlow(RepairsFlow):
    def __init__(self, entry_id: str, key: str) -> None:
        self._entry_id, self._key = entry_id, key

    @property
    def _advisor(self):
        coordinator = self.hass.data.get(DOMAIN, {}).get(self._entry_id, {}).get("coordinator")
        return coordinator.advisor if coordinator else None

    def _placeholders(self) -> dict[str, str]:
        from homeassistant.helpers import issue_registry as ir

        issue = ir.async_get(self.hass).async_get_issue(self.handler, self.issue_id)
        return dict(issue.translation_placeholders or {}) if issue else {}

    async def async_step_init(self, user_input=None):
        advisor = self._advisor
        advice = advisor.find(self._key) if advisor else None
        if advice is None:
            return self.async_abort(reason="advice_gone")
        options = ["apply", "snooze"] if advice.applicable else ["snooze"]
        return self.async_show_menu(
            step_id="init", menu_options=options, description_placeholders=self._placeholders()
        )

    async def async_step_snooze(self, user_input=None):
        await self._advisor.async_snooze(self._key)
        return self.async_create_entry(data={})

    async def async_step_apply(self, user_input=None):
        advice = self._advisor.find(self._key)
        if advice is None:
            return self.async_abort(reason="advice_gone")
        if advice.kind == "occupants" and user_input is None:
            schema = vol.Schema(
                {
                    vol.Required("people", default=list(advice.people)): selector.EntitySelector(
                        selector.EntitySelectorConfig(
                            domain=["person", "device_tracker", "binary_sensor", "input_boolean", "switch"],
                            multiple=True,
                        )
                    )
                }
            )
            return self.async_show_form(
                step_id="apply", data_schema=schema, description_placeholders=self._placeholders()
            )
        # Close the issue first: applying reloads the integration.
        result = self.async_create_entry(data={})
        await self._advisor.async_apply(self._key, (user_input or {}).get("people", ()))
        return result


async def async_create_fix_flow(hass: HomeAssistant, issue_id: str, data: dict) -> RepairsFlow:
    return AdviceFlow(data["entry_id"], data["key"])
