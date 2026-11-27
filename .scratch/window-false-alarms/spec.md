# Release A: Open-window false alarms

Status: resolved
Order: 2 of 6

## Problem
A Room with a room sensor and a TRV that reports its valve shows many short drops to frost-hold in
a day, during comfort and setback, matching open-window pauses with no open window. Its learned
window threshold was 0.8 K (so a single 0.5 K sensor step is not the explanation).

The room sensor of the affected Room reports in 0.5 K steps. With a 0.8 K threshold, two steps down
within the detection period (1.0 K) would already trigger if the room sensor is what is judged.

## Hypothesis (unproven)
When the TRV reports its valve, the fast fall is judged on the TRV sensor without checking the room
sensor (`engine/window.py`, `_fast_fall`), so the valve sensor cooling after the valve closes
(for example when the Room is satisfied) reads as an open window.

Second candidate: while the radiator cools down the room sensor is judged alone, where such a two-step
fall pauses the Room.

## Work
- Reproduce with a failing test first (diagnosing-bugs). Confirm or reject the hypothesis, using
  the history export when available.
- Fix the cause. A real open window must still be detected.
- Cover a 0.5 K step sensor in tests: ordinary two-step swings around the target are no window.

## Data
History CSV exports are for local tuning only and are never committed. Fixtures are synthetic.

## Comments

Hypothesis confirmed by a local history export: with the valve reported 72-100 % open the TRV sensor
fell 1.7 K in eight minutes while the room sensor rose, and the Room paused. Fix: a fresh room sensor
must now confirm a TRV-sensor fall whether or not the valve is reported, and a sensor with nothing new
to report does not confirm. The cooling-down path (room sensor alone) showed no false alarm in the
export and is unchanged.
