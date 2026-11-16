# Smart Heating

[![Open in the Home Assistant Marketplace](https://my.home-assistant.io/badges/marketplace_repository.svg)](https://my.home-assistant.io/redirect/marketplace_repository/?owner=stijnb1234&repository=ha-smart-heating&category=integration)
[![Release](https://img.shields.io/github/v/release/stijnb1234/ha-smart-heating)](https://github.com/stijnb1234/ha-smart-heating/releases)
[![Validate](https://github.com/stijnb1234/ha-smart-heating/actions/workflows/validate.yml/badge.svg)](https://github.com/stijnb1234/ha-smart-heating/actions/workflows/validate.yml)
[![License: MIT](https://img.shields.io/github/license/stijnb1234/ha-smart-heating)](https://github.com/stijnb1234/ha-smart-heating/blob/main/LICENSE)

Room-by-room heating for Home Assistant. One boiler, several radiators: the boiler fires only when a room actually wants heat, and rooms nobody uses stay cool.

Smart Heating sets each room's target temperature from a schedule, presence, Boost and Vacation mode, drives your smart radiator valves (TRVs), and calls the boiler only while at least one room is too cold. It learns how fast each room warms up, so rooms are comfortable at the time you want them, without heating all day.

**Living with it?** The user manual explains the Overview screen, the buttons and what each message means, without the technical details: [English](https://github.com/stijnb1234/ha-smart-heating/blob/main/docs/manual.en.md) · [Nederlands](https://github.com/stijnb1234/ha-smart-heating/blob/main/docs/manual.nl.md).

<!-- ha-marketplace:exclude-start -->
**Contents:** [Features](#features) · [Requirements](#requirements) · [Installation](#installation) · [Getting started](#getting-started) · [Configuration](#configuration) · [Dashboard](#dashboard) · [Entities](#entities) · [Services](#services) · [How decisions are made](#how-decisions-are-made) · [Troubleshooting](#troubleshooting) · [Contributing](#contributing)
<!-- ha-marketplace:exclude-end -->

## Features

### Rooms and the boiler

- **Target per room** from schedule, presence, Boost and Vacation (defaults: comfort 19.5 °C, setback 16 °C, frost-hold 12 °C).
- **Any smart TRV** that Home Assistant shows as a `climate` entity (Zigbee2MQTT, ZHA, cloud valves): setpoint, calibration, and a valve that is switched off is turned back on. Extras found on the valve's device are used when present: battery, valve opening, heating demand and an **external room temperature** input (a number entity in °C, or Zigbee2MQTT over MQTT), so the valve regulates on the room's own thermometer. A valve that cannot take one gets its setpoint corrected instead.
- **Boiler call** by raising the setpoint of a boiler thermostat (any `climate` entity that makes the boiler fire) only while a room has unmet demand. Debounced, rate-limit safe, with a timeout so a hung cloud call does not stall the rest.
- **Pre-heat** so rooms are warm at schedule time. The lead time is learned per room from past warm-ups and the outdoor temperature, and follows how far the room has to come right now.
- **Open-radiator rooms** (no smart valve yet, sensor required) and **floor-heating rooms** (always-open loops, sensor required, long pre-heat) call the boiler too.

### Presence

- **Away**: everyone out drops rooms to setback, and after 48 h to frost-hold. The count survives restarts.
- **Heading home, automatically**: from the position the Home Assistant app reports, Smart Heating sees someone approaching at travel speed and ends Away early so the house is warm on arrival. No zones to draw.
- **Vacation**: set a return moment by hand, with a service, or from a calendar. Each room starts warming up just in time for your return.
- **Per-room occupants**: while all people linked to a room are away, the room skips its schedule.

### Automatic behaviour

- **Open-window detection**: a fast temperature drop pauses a room for 15–30 minutes. It ignores the false drops a radiator causes when it cools: it uses the valve state and the room sensor, and times readings by when the sensor reported them. A threshold learned per room (never looser than the one you configure) fits each room's own noise.
- **Self-learning**, persisted per room with safe fallbacks until there is data: how far a room keeps warming after the boiler call ends (so the call ends earlier and does not overshoot), the difference between the room sensor and the TRV sensor, and habits that suggest schedule changes.
- **Hand changes are respected**: a temperature set on a valve stays until that room's target next changes; a change on the boiler thermostat is respected for 2 hours.
- **Lost writes are repaired**: a TRV that did not take a setpoint gets it again. A TRV that is out of reach does not use up retries, and is written to as soon as it is back.

### Control and insight

- **Boost** buttons and service, and a **Manual-room override** that calls the boiler for rooms with ordinary valves.
- **Alerts** for TRV offline or switched off, a TRV not accepting its setpoint, low battery, a room that does not warm up, a boiler thermostat that is unreachable and stale sensors. Shown under the bell, and optionally pushed to your phone after a delay, with a message when resolved.
- **Weekly gas report** every Monday: m³ per heating-degree-day versus last year, hours each room called the boiler, open issues.
- A generated **dashboard** with a plain-language overview, a page per room, a boiler page and help.
- **English and Dutch**, following Home Assistant's language.
- **Rename rooms freely**: each room has a stable id, so entities, history and learned data survive.

Not controlled: the floor loops themselves (floor heating only calls the boiler) and dumb TRVs (except through the Manual-room override).

## Requirements

- Home Assistant **2025.1 or newer**. The built-in Marketplace needs 2026.11; on older versions install through HACS.
- Smart TRVs as `climate.*` entities. For the external room temperature: a number entity on the valve's device, or Zigbee2MQTT with the MQTT integration.
- A boiler thermostat as a `climate.*` entity (optional: without it no boiler call is made).
- Optional: `person.*` entities and the Home Assistant app with location (presence), a calendar entity (vacations), a gas meter and an outdoor temperature sensor with long-term statistics (weekly report).

## Installation

### Home Assistant Marketplace (2026.11 and newer)

1. Click the badge at the top, or go to **Settings → Marketplace**.
2. Select **Add from link**, enter `https://github.com/stijnb1234/ha-smart-heating` and select **Add**. (This needs a connected GitHub account, which the Marketplace asks for. Once Smart Heating is in the default catalog, you can just search for it.)
3. Open **Smart Heating** and install it. Restart Home Assistant.
4. **Settings → Devices & services → Add integration → Smart Heating**.

### HACS (older Home Assistant versions)

1. HACS → ⋮ → **Custom repositories**, add `https://github.com/stijnb1234/ha-smart-heating` as **Integration**.
2. Download **Smart Heating**, restart Home Assistant and add the integration as above.

### Manual

Copy `custom_components/smart_heating` into your config's `custom_components/` folder and restart.

## Getting started

1. **Add the integration** and open **Configure**.
2. **Set the boiler**: pick the boiler thermostat under *Boiler, presence and vacation*, and the people to track.
3. **Add a room**: name, TRV entity, an optional external temperature sensor, temperatures and a schedule preset (living area, working room, bedroom) or your own schedule text.
4. Open the **Smart Heating** dashboard in the sidebar. The status line tells you what is happening and why. Give it a few days: warm-up times and coast are learned from real heating cycles.

Tips for good results:

- Give rooms an **external temperature sensor** where you can: the TRV's own sensor sits on the hot radiator.
- With **Zigbee2MQTT**, keep availability enabled so a TRV that stops responding turns `unavailable`.
- A mains-powered Zigbee router near battery TRVs helps keep them connected.

## Configuration

Everything is configured in the UI under **Settings → Devices & services → Smart Heating → Configure**. Changes apply without a restart.

| Menu | What you set |
|---|---|
| Add / edit / remove a room | Name, TRV entity, optional external sensor, comfort / setback / frost-hold, schedule, offset, lead time, window detection, occupants. Rooms flagged *manual* have no TRV; *floor heating* and *open radiator* rooms need a sensor. |
| Boiler, presence and vacation | Boiler thermostat, tracked persons, heading-home detection, vacation calendar and keywords, boiler low / high setpoints, Boost and override durations, bedroom pre-bed window. |
| Boiler call and alert thresholds | Debounce, backoff, demand hysteresis, alert thresholds, battery %, notify services for alerts and their delay, Zigbee2MQTT base topic. |
| Gas report settings | Gas meter entity, outdoor sensor, heating-degree-day base (default 18 °C). |

Schedule text: one comfort window per line.

```
daily 06:00-23:00
mon,wed,fri 08:00-17:00
mon-fri 07:00-09:00
```

Dutch day names (ma, di, wo, do, vr, za, zo, dagelijks) work too.

## Dashboard

On setup the integration writes `smart_heating_dashboard.yaml` into your config folder and registers a **Smart Heating** dashboard in the sidebar.

| Page | Contents |
|---|---|
| Overview | Status line, a table of all rooms (temperature now, target, plain sentence), alerts and all controls. |
| Heating | A section per room: summary, next change, lead time, Boost, a 24 h graph and the valve's battery, opening and heating demand. |
| Boiler | Call status, demand rooms, last write and its result, backoff, manual hold, Manual-room override. |
| Help | Short cards on how to read the dashboard. |

If automatic registration fails (see the log), register the file yourself:

```yaml
lovelace:
  dashboards:
    smart-heating:
      mode: yaml
      title: Smart Heating
      icon: mdi:radiator
      show_in_sidebar: true
      filename: smart_heating_dashboard.yaml
```

## Entities

Per room (`<domain>.smart_heating_<room id>[_<key>]`): a read-only `climate` (its action is *heating* only while the room calls the boiler), sensors for *reason*, *summary*, *next change* and *lead time*, and Boost and cancel-boost buttons.

System-wide: a Vacation `switch` and return `datetime`, Manual-room override buttons, `sensor.smart_heating_status`, `sensor.smart_heating_active_alerts`, `binary_sensor.smart_heating_boiler_call` and `sensor.smart_heating_boiler_*`.

## Services

| Service | What it does |
|---|---|
| `smart_heating.boost` | Target room climate entities; optional `duration` (default: the configured Boost). |
| `smart_heating.cancel_boost` | Stop a Boost. |
| `smart_heating.set_vacation` | `end` (when you are back), optional `start` (default now). |
| `smart_heating.cancel_vacation` | End a manual vacation. |

Example: warm the bathroom for 20 minutes when the alarm goes off.

```yaml
action: smart_heating.boost
target:
  entity_id: climate.smart_heating_bathroom
data:
  duration: "00:20:00"
```

## How decisions are made

Target precedence per room: **Boost > open-window pause > Vacation > Away > schedule (with pre-heat) > setback**. The boiler is called only for rooms whose target is comfort and whose temperature is below it by more than the hysteresis, plus hand-set valves.

All decision logic lives in a pure Python engine (`custom_components/smart_heating/engine/`) with no Home Assistant imports, tested with a fake clock. See [GLOSSARY.md](https://github.com/stijnb1234/ha-smart-heating/blob/main/GLOSSARY.md), [docs/design.md](https://github.com/stijnb1234/ha-smart-heating/blob/main/docs/design.md) and [docs/adr/](https://github.com/stijnb1234/ha-smart-heating/blob/main/docs/adr).

## Troubleshooting

- **Boiler never fires**: check the boiler thermostat is set under *Boiler, presence and vacation* and that its integration can write setpoints. Look for `boiler_outage` alerts.
- **A room shows "–" as its temperature**: no fresh reading. A TRV reading counts for 6 hours and an external sensor for 1 hour; battery TRVs only report when the temperature changes.
- **"TRV does not accept its temperature"**: the valve kept its old setpoint after repeated writes. Smart Heating keeps trying every 30 minutes. A weak Zigbee link or a sleeping battery TRV is the usual cause; check its link quality and a nearby router.
- **Window pause when nothing was open**: the log line `Open window in <room>: …` shows the drop, both sensors' recent readings and the valve state. Include it in a bug report.
- **Room ignores its external sensor**: check the diagnostics for whether the valve takes an external temperature at all.

Still stuck? Open an [issue](https://github.com/stijnb1234/ha-smart-heating/issues/new/choose) with the diagnostics (**Settings → Devices & services → Smart Heating → ⋮ → Download diagnostics**; people and calendars are redacted, locations are never included) and debug logs (`custom_components.smart_heating: debug`).

<!-- ha-marketplace:exclude-start -->
## Contributing

Bug reports, ideas and pull requests are welcome; see [CONTRIBUTING.md](CONTRIBUTING.md).

```bash
python3.13 -m venv .venv && .venv/bin/pip install -r requirements-test.txt
.venv/bin/ruff check .   # lint
.venv/bin/mypy           # types
.venv/bin/pytest -q      # engine tests plus Home Assistant smoke tests
```

Releasing: bump `version` in `manifest.json`, then push a tag `v<version>`. The release workflow checks they match and publishes the GitHub release.

Security issues: see [SECURITY.md](SECURITY.md).
<!-- ha-marketplace:exclude-end -->

## License

[MIT](https://github.com/stijnb1234/ha-smart-heating/blob/main/LICENSE)
