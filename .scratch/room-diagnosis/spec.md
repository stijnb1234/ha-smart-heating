# Release B: One diagnosis per Room, fewer pushes

Status: ready-for-agent
Order: 4 of 6

## Problem
Every condition is its own alert and can be pushed, so one broken valve produces several messages
and none says how to fix it.

## Design
- Symptoms of a Room (stalled, target not reached, TRV offline / off / rejecting its temperature,
  sensor stale, low battery) are merged into one diagnosis: likely cause and steps to solve it.
- Immediate phone push only for: boiler thermostat unreachable, and frost risk.
- Frost risk: a Room within 1 K of frost-hold that is still falling or flat for 1 hour.
- Everything else becomes Advice only after recurring: at least 3 occurrences. Until release C
  exists, diagnoses stay visible on the dashboard.
- Texts in en and nl, generic for any home.
