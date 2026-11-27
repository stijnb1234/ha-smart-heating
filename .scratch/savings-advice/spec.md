# Release C: Advice in Home Assistant Repairs

Status: ready-for-agent
Order: 5 of 6
Decision: docs/adr/0008-local-advice-in-repairs.md

## Goal
Detect recurring patterns that waste gas and tell the administrator how to solve them.

## Evidence
Existing data only: presence, Room occupants, Boost, hand-set valves, temperatures, boiler calls,
valve reports. Compact daily summaries in own storage. No occupancy sensors. Never claim a room was
unused, only that its people were away. Wording is about Rooms, not persons.

## Threshold
Savings advice: same weekday and time slot, at least 3 occurrences within 4 weeks, true at least
75 % of the time, saving at least 1 boiler hour per week. Fault diagnoses (release B) may show
after 3 occurrences.

## Advice types, in build order
1. Radiator heats while it should be closed (top priority; includes sun as a possible cause when
   only seen in daytime). Steps: valve mounting, calibration, batteries, sensor placement.
2. A Room alone keeps the boiler on: hours per week, options (later start, lower comfort) as text.
3. Pre-heat very long or finishing late: steadier schedule or smaller setback. Floor heating is
   included.
4. Trim schedule (shorten, later start, drop a weekday). Apply.
5. Add schedule time (existing suggestion). Apply.
6. Link Room occupants. Apply; the fix dialog asks which people.

Rooms without a room sensor: only type 1 (worded "probably") and the advice to add a room sensor;
no temperature or schedule advice.

## Ranking
By boiler hours the Room alone caused (a shared call saves about nothing). "About" money only with
a gas meter and the new optional gas price setting.

## Interaction
- Home Assistant Repairs, administrator only; the dashboard shows a read-only list.
- Apply is always a deliberate click, never automatic. Snooze (4 weeks) is offered in the fix
  dialog; dismiss is the Repairs ignore.
- A button and an action undo the last applied advice; kept 4 weeks.
- Detection is pure engine code, tested with a fake clock. Texts in en and nl.
