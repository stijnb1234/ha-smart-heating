# Release A2: Guided calibration for Rooms without a room sensor

Status: resolved
Order: 3 of 6

## Problem
Without a room sensor the Room temperature comes from the TRV next to the radiator. It reads roughly
right with a cold radiator and several degrees high with a hot one.

## Design
- The user places a thermometer in the room, away from the radiator, and enters its reading.
- Smart Heating records the entry with the TRV reading and the radiator state (cold or heating).
- Both states are needed once; Smart Heating asks for the missing one when the Room is in that state.
- The applied offset follows the radiator state. More entries refine it.
- Existing `trv_offset` and the learned external-sensor offset keep their meaning; define
  precedence: room sensor > calibration > fixed offset.
- Radiator state uses the valve report where available, else the radiator cooldown tracking.
- Calibration survives restarts, can be cleared, and is included in diagnostics.
- Texts in en and nl.
