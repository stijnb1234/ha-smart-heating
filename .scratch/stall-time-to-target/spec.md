# Release 0: Stalled Rooms, including slow crawlers

Status: resolved
Order: 1 of 6

## Problem
A Room that cannot reach its target must not hold the boiler on. The implemented Stalled Room rule
(no 0.3 K rise within 45 min, floor heating 3 h; rest 3 h, retry) misses a Room that creeps up
just fast enough to count as progress while its target stays out of reach.

## Add
- A Room is also stalled when, at its current rise rate, reaching the target would take more than
  6 hours. Floor-heating Rooms are excluded from this rule.
- The rate is measured over a long enough window that a 0.5 K step sensor does not trigger it.
- Rest, retry, recovery, Boost reset and alert behaviour are those of a Stalled Room. Recovery must
  not be granted by a creep that would itself be judged stalled.
- Update glossary, manuals and alert text where they describe the rule.

## Done when
Engine tests cover: crawler is stalled, healthy slow Room is not, 0.5 K sensor is not, floor
heating is not. The uncommitted base fix ships in the same release.
