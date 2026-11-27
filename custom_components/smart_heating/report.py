"""Pure weekly digest: a gas verdict, what to do and what earlier changes did. No Home Assistant imports.

Gas use is normalised as m3 per heating-degree-day (HDD) so a cold week and a
mild week compare fairly, and this week is compared with the same period last year.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from .i18n import DEFAULT_LANGUAGE, number, tr

DEFAULT_HDD_BASE = 18.0
TOP_ACTIONS = 3
# A change in gas use this large is worth a message even without anything to do.
NOTABLE_CHANGE_PCT = 10.0


def heating_degree_days(daily_mean_temps: Sequence[float], base: float = DEFAULT_HDD_BASE) -> float:
    return sum(max(0.0, base - t) for t in daily_mean_temps)


def m3_per_hdd(gas_m3: float | None, temps: Sequence[float], base: float) -> float | None:
    """None when gas is unknown or there were no heating degree-days."""
    if gas_m3 is None:
        return None
    hdd = heating_degree_days(temps, base)
    if hdd <= 0:
        return None
    return gas_m3 / hdd


def gas_change_pct(
    gas_m3: float | None,
    temps: Sequence[float],
    last_gas_m3: float | None,
    last_temps: Sequence[float],
    base: float = DEFAULT_HDD_BASE,
) -> float | None:
    """Weather-corrected change in gas use against the same week last year."""
    now, before = m3_per_hdd(gas_m3, temps, base), m3_per_hdd(last_gas_m3, last_temps, base)
    if now is None or not before:
        return None
    return (now / before - 1) * 100


@dataclass(frozen=True)
class Digest:
    change_pct: float | None = None
    actions: Sequence[str] = ()  # most valuable first
    effects: Sequence[tuple[str, float, float]] = ()  # (Room, hours per week before, since)

    @property
    def worth_sending(self) -> bool:
        return bool(self.actions or self.effects) or (
            self.change_pct is not None and abs(self.change_pct) >= NOTABLE_CHANGE_PCT
        )

    def verdict(self, lang: str = DEFAULT_LANGUAGE) -> str | None:
        if self.change_pct is None:
            return None
        pct = round(self.change_pct)
        if pct == 0:
            return tr(lang, "digest.same")
        return tr(lang, "digest.less" if pct < 0 else "digest.more", pct=abs(pct))

    def format(self, lang: str = DEFAULT_LANGUAGE) -> str:
        blocks = []
        if verdict := self.verdict(lang):
            blocks.append(verdict)
        if self.actions:
            top = [f"{i}. {a}" for i, a in enumerate(self.actions[:TOP_ACTIONS], 1)]
            blocks.append("\n".join([tr(lang, "digest.actions"), *top]))
        if self.effects:
            blocks.append(
                "\n".join(
                    [
                        tr(lang, "digest.effects"),
                        *(
                            tr(lang, "digest.effect", room=r, before=number(b, lang), after=number(a, lang))
                            for r, b, a in self.effects
                        ),
                    ]
                )
            )
        return "\n\n".join(blocks)

    def short(self, lang: str = DEFAULT_LANGUAGE) -> str:
        """One or two lines for a phone."""
        parts = [v] if (v := self.verdict(lang)) else []
        if self.actions:
            parts.append(tr(lang, "digest.push_actions", count=len(self.actions[:TOP_ACTIONS])))
        return " ".join(parts) or tr(lang, "digest.title")
