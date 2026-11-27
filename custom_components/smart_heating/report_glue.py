"""Thin HA glue for the weekly digest: gather data, call report.py, notify.

Unit-tested logic lives in report.py. This file is only verified in a real HA.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from .advice_actions import advice_text, effects
from .alerts_adapter import notify_service
from .apply import call_service
from .const import (
    CONF_GAS_ENTITY,
    CONF_GAS_PRICE,
    CONF_HDD_BASE,
    CONF_NOTIFY_TARGETS,
    CONF_OUTDOOR_ENTITY,
    DOMAIN,
)
from .i18n import tr
from .report import DEFAULT_HDD_BASE, Digest, gas_change_pct

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

REPORT_WEEKDAY = 0  # Monday
REPORT_HOUR = 8
YEAR_AGO = timedelta(weeks=52)  # whole weeks so weekdays line up


async def _daily_stats(hass, entity_id, start, end, stat_type):
    from homeassistant.components.recorder import get_instance
    from homeassistant.components.recorder.statistics import statistics_during_period

    result = await get_instance(hass).async_add_executor_job(
        statistics_during_period, hass, start, end, {entity_id}, "day", None, {stat_type}
    )
    rows: list[dict] = [dict(row) for row in result.get(entity_id, [])]
    return [row[stat_type] for row in rows if row.get(stat_type) is not None]


async def _gas_and_temps(hass, gas, outdoor, start, end):
    changes = await _daily_stats(hass, gas, start, end, "change") if gas else []
    temps = await _daily_stats(hass, outdoor, start, end, "mean") if outdoor else []
    return (sum(changes) if changes else None), temps


async def async_send_report(hass: HomeAssistant, entry: ConfigEntry) -> None:
    from homeassistant.util import dt as dt_util

    shared = hass.data.get(DOMAIN, {}).get(entry.entry_id, {})
    coordinator = shared.get("coordinator")
    if coordinator is None:
        return
    lang = coordinator.lang
    opts = entry.options
    base = float(opts.get(CONF_HDD_BASE, DEFAULT_HDD_BASE))
    end = dt_util.now().replace(minute=0, second=0, microsecond=0)
    start = end - timedelta(days=7)
    gas, outdoor = opts.get(CONF_GAS_ENTITY), opts.get(CONF_OUTDOOR_ENTITY)

    this_gas, temps = await _gas_and_temps(hass, gas, outdoor, start, end)
    last_gas, last_temps = await _gas_and_temps(hass, gas, outdoor, start - YEAR_AGO, end - YEAR_AGO)

    # What one boiler hour costs, roughly: the gas meter also counts hot water and cooking.
    advisor = coordinator.advisor
    log = coordinator.controller.advice_log
    hours = sum(m for d, m in log.boiler.items() if d >= start.date().isoformat()) / 60
    price = opts.get(CONF_GAS_PRICE)
    advisor.state.cost_per_hour = this_gas / hours * float(price) if price and this_gas and hours >= 1 else None
    advisor.state.currency = hass.config.currency
    await advisor.async_refresh()

    digest = Digest(
        change_pct=gas_change_pct(this_gas, temps, last_gas, last_temps, base),
        actions=[
            advice_text(a, lang, advisor.state.cost_per_hour, advisor.names(), advisor.state.currency)
            for a in advisor.current
        ],
        effects=effects(advisor.state, log, dt_util.now()),
    )
    if not digest.worth_sending:
        return
    await call_service(
        hass,
        "persistent_notification",
        "create",
        {
            "title": tr(lang, "digest.title"),
            "message": digest.format(lang),
            "notification_id": f"smart_heating_report_{entry.entry_id}",
        },
    )
    for target in opts.get(CONF_NOTIFY_TARGETS, []):
        if service := notify_service(target):
            await call_service(
                hass, "notify", service, {"title": tr(lang, "digest.title"), "message": digest.short(lang)}
            )


def schedule_weekly_report(hass: HomeAssistant, entry: ConfigEntry):
    """Fire Mondays 08:00 local time. Returns the unsubscribe callable."""
    from homeassistant.helpers.event import async_track_time_change

    async def _fire(now: datetime) -> None:
        if now.weekday() == REPORT_WEEKDAY:
            await async_send_report(hass, entry)

    return async_track_time_change(hass, _fire, hour=REPORT_HOUR, minute=0, second=0)
