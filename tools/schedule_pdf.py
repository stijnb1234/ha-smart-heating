"""Turn a Smart Heating diagnostics export into a printable schedule overview (PDF).

Handy for talking through the weekly schedules with the people you live with.

    python tools/schedule_pdf.py config_entry-smart_heating-XXXX.json schedule.pdf --lang en

The input is the JSON from Settings > Devices & services > Smart Heating > Download diagnostics.
Needs `reportlab` (see tools/requirements.txt). Not part of the integration itself.
"""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas

TEXTS: dict[str, dict[str, Any]] = {
    "nl": {
        "days": ["Maandag", "Dinsdag", "Woensdag", "Donderdag", "Vrijdag", "Zaterdag", "Zondag"],
        "short": ["Ma", "Di", "Wo", "Do", "Vr", "Za", "Zo"],
        "title": "Verwarmingsschema",
        "overview": "{n} kamers · overzicht per week",
        "floor": "Vloerverwarming",
        "open_radiators": "Open radiatoren",
        "manual": "Handbediende kraan",
        "trv": "Slimme radiatorkraan",
        "legend_comfort": "Comfort: de kamer wordt warm gehouden",
        "legend_setback": "Spaarstand: de kamer mag afkoelen (ook als er niemand thuis is)",
        "not_heated": "niet verwarmd",
        "axis_note": "Elke balk loopt van 06:00 tot 24:00. Onder de kamernaam: type kraan, daaronder de comfort- / spaartemperatuur.",
        "card_comfort": ("Comfort", "temperatuur in de comforturen"),
        "card_setback": ("Spaarstand", "buiten de comforturen"),
        "card_frost": ("Vorstbeveiliging", "bij lange afwezigheid of raam open"),
        "room_sub": "{kind} · {hours:.1f} uur comfort per week",
        "hours": "{h:.1f} u",
        "off": "uit",
        "discuss": "Bespreken",
        "box_left": "Wat werkt goed / niet goed?",
        "box_right": "Gewenste wijziging (dagen en tijden)",
        "points_title": "Om te bespreken",
        "points_sub": "wat opvalt in de huidige schema's",
        "points_more": "vervolg",
        "footer": "Verwarmingsschema, gemaakt op {date}",
        "page": "Pagina {n}",
        "date": "%d-%m-%Y",
        "no_comfort_days": "Op {days} staat er helemaal geen comfortperiode. Klopt dat met wie er thuis is?",
        "no_schedule": "Heeft geen schema; de kamer blijft op de spaartemperatuur.",
        "nobody_daytime": "Overdag (09:00-17:00) wordt geen enkele kamer verwarmd.",
        "daytime_title": "Overdag op werkdagen",
        "daytime_text": "Wie wordt overdag verwarmd? {sample}.",
        "nobody": "niemand",
        "same_schedule": "Hebben exact hetzelfde schema.{extra} Is dat de bedoeling?",
        "temps_differ": " De temperaturen verschillen.",
        "static_points": [
            (
                "Voorverwarmen",
                "Een kamer begint al eerder te verwarmen zodat hij op de starttijd warm is. Dat leert het systeem zelf, rond de 70 minuten bij een koude start. Reken daarop bij de starttijden.",
            ),
            (
                "Niemand thuis",
                "Als iedereen weg is, vallen alle kamers terug naar de spaarstand. Na 48 uur naar vorstbeveiliging. Het schema hoeft daar niet voor aangepast te worden.",
            ),
            ("Raam open", "Een snelle temperatuurdaling pauzeert de kamer 15 tot 30 minuten op vorstbeveiliging."),
        ],
    },
    "en": {
        "days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
        "short": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        "title": "Heating schedule",
        "overview": "{n} rooms · weekly overview",
        "floor": "Floor heating",
        "open_radiators": "Open radiators",
        "manual": "Manual valve",
        "trv": "Smart radiator valve",
        "legend_comfort": "Comfort: the room is kept warm",
        "legend_setback": "Setback: the room may cool down (also when nobody is home)",
        "not_heated": "not heated",
        "axis_note": "Every bar runs from 06:00 to 24:00. Under the room name: valve type, then the comfort / setback temperature.",
        "card_comfort": ("Comfort", "temperature during comfort hours"),
        "card_setback": ("Setback", "outside comfort hours"),
        "card_frost": ("Frost protection", "when away for long or window open"),
        "room_sub": "{kind} · {hours:.1f} comfort hours per week",
        "hours": "{h:.1f} h",
        "off": "off",
        "discuss": "To discuss",
        "box_left": "What works well / not so well?",
        "box_right": "Wanted change (days and times)",
        "points_title": "Talking points",
        "points_sub": "what stands out in the current schedules",
        "points_more": "continued",
        "footer": "Heating schedule, created on {date}",
        "page": "Page {n}",
        "date": "%Y-%m-%d",
        "no_comfort_days": "There is no comfort period at all on {days}. Does that match who is home?",
        "no_schedule": "Has no schedule; the room stays at the setback temperature.",
        "nobody_daytime": "No room is heated during the day (09:00-17:00).",
        "daytime_title": "Daytime on weekdays",
        "daytime_text": "Who is heated during the day? {sample}.",
        "nobody": "nobody",
        "same_schedule": "Have exactly the same schedule.{extra} Is that intended?",
        "temps_differ": " The temperatures differ.",
        "static_points": [
            (
                "Pre-heating",
                "A room starts heating earlier so it is warm at the start time. The system learns this itself, around 70 minutes from a cold start. Take that into account when choosing start times.",
            ),
            (
                "Nobody home",
                "When everyone is away, all rooms fall back to setback, and to frost protection after 48 hours. The schedule does not need to change for that.",
            ),
            ("Window open", "A fast temperature drop pauses the room at frost protection for 15 to 30 minutes."),
        ],
    },
}

COMFORT = colors.HexColor("#F08A3C")
COMFORT_DARK = colors.HexColor("#B85A12")
SETBACK = colors.HexColor("#E3ECF4")
INK = colors.HexColor("#1F2933")
MUTED = colors.HexColor("#6B7785")
LINE = colors.HexColor("#C9D2DC")
ACCENT = colors.HexColor("#2F6690")
STRIPE = colors.HexColor("#F7F9FB")

PAGE = landscape(A4)
W, H = PAGE
MM = 2.835
M = 14 * MM
AX0, AX1 = 6 * 60, 24 * 60  # time axis shown: 06:00-24:00

Blocks = list[tuple[int, int]]


def minutes(text: str) -> int:
    hours, mins = text.split(":")
    return int(hours) * 60 + int(mins)


def hhmm(mins: int) -> str:
    return f"{mins // 60:02d}:{mins % 60:02d}"


def blocks_per_day(room: dict[str, Any]) -> dict[int, Blocks]:
    """Comfort blocks per weekday (0 = Monday) as merged (start, end) minute pairs."""
    per_day: dict[int, Blocks] = {d: [] for d in range(7)}
    for window in room.get("schedule", []):
        for day in window["days"]:
            per_day[day].append((minutes(window["start"]), minutes(window["end"])))
    for day, blocks in per_day.items():
        merged: Blocks = []
        for start, end in sorted(blocks):
            if merged and start <= merged[-1][1]:
                merged[-1] = (merged[-1][0], max(merged[-1][1], end))
            else:
                merged.append((start, end))
        per_day[day] = merged
    return per_day


def axis_x(mins: int, x0: float, x1: float) -> float:
    mins = min(max(mins, AX0), AX1)
    return x0 + (mins - AX0) / (AX1 - AX0) * (x1 - x0)


class Report:
    def __init__(self, rooms: list[dict[str, Any]], out: Path, lang: str) -> None:
        self.rooms = rooms
        self.t = TEXTS[lang]
        self.c = canvas.Canvas(str(out), pagesize=PAGE)
        self.c.setTitle(self.t["title"])
        self.c.setAuthor("Smart Heating")
        self.page_no = 1

    # -- building blocks -------------------------------------------------

    def kind(self, room: dict[str, Any]) -> str:
        if room.get("floor_heating"):
            return self.t["floor"]
        if room.get("open_radiators"):
            return self.t["open_radiators"]
        if room.get("manual"):
            return self.t["manual"]
        return self.t["trv"]

    def header(self, title: str, subtitle: str | None = None) -> None:
        c = self.c
        c.setFillColor(ACCENT)
        c.rect(0, H - 22 * MM, W, 22 * MM, stroke=0, fill=1)
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 20)
        c.drawString(M, H - 14.5 * MM, title)
        if subtitle:
            c.setFont("Helvetica", 11)
            c.drawRightString(W - M, H - 14.5 * MM, subtitle)

    def footer(self) -> None:
        c = self.c
        c.setFillColor(MUTED)
        c.setFont("Helvetica", 8)
        today = date.today().strftime(self.t["date"])
        c.drawString(M, 8 * MM, self.t["footer"].format(date=today))
        c.drawRightString(W - M, 8 * MM, self.t["page"].format(n=self.page_no))

    def next_page(self) -> None:
        self.footer()
        self.c.showPage()
        self.page_no += 1

    def legend(self, x: float, y: float) -> None:
        c = self.c
        c.setFillColor(COMFORT)
        c.roundRect(x, y - 2, 14, 9, 2, stroke=0, fill=1)
        c.setFillColor(INK)
        c.setFont("Helvetica", 9)
        c.drawString(x + 19, y, self.t["legend_comfort"])
        offset = x + 19 + c.stringWidth(self.t["legend_comfort"], "Helvetica", 9) + 22
        c.setFillColor(SETBACK)
        c.setStrokeColor(LINE)
        c.roundRect(offset, y - 2, 14, 9, 2, stroke=1, fill=1)
        c.setFillColor(INK)
        c.drawString(offset + 19, y, self.t["legend_setback"])

    def timeline(
        self, x0: float, y: float, x1: float, h: float, blocks: Blocks, labels: bool = True, font: float = 8
    ) -> None:
        c = self.c
        c.setFillColor(SETBACK)
        c.setStrokeColor(LINE)
        c.roundRect(x0, y, x1 - x0, h, 2, stroke=1, fill=1)
        for start, end in blocks:
            xa, xb = axis_x(start, x0, x1), axis_x(end, x0, x1)
            c.setFillColor(COMFORT)
            c.rect(xa, y, xb - xa, h, stroke=0, fill=1)
            if labels and xb - xa > 46:
                c.setFillColor(colors.white)
                c.setFont("Helvetica-Bold", font)
                c.drawCentredString((xa + xb) / 2, y + h / 2 - font / 3, f"{hhmm(start)}-{hhmm(end)}")

    def hour_grid(self, x0: float, y0: float, x1: float, y1: float, label_y: float) -> None:
        c = self.c
        c.setStrokeColor(LINE)
        c.setLineWidth(0.4)
        c.setFillColor(MUTED)
        c.setFont("Helvetica", 7)
        for hour in range(AX0 // 60, AX1 // 60 + 1, 2):
            x = axis_x(hour * 60, x0, x1)
            c.line(x, y0, x, y1)
            c.drawCentredString(x, label_y, f"{hour:02d}:00")
        c.setLineWidth(1)

    # -- pages -----------------------------------------------------------

    def overview(self) -> None:
        c, t = self.c, self.t
        self.header(t["title"], t["overview"].format(n=len(self.rooms)))
        self.legend(M, H - 30 * MM)

        grid_x0 = M + 38 * MM
        col_w = (W - M - grid_x0) / 7
        top = H - 38 * MM
        head_h = 12
        row_h = (top - 18 * MM - head_h) / len(self.rooms)

        c.setFont("Helvetica-Bold", 10)
        c.setFillColor(ACCENT)
        for d in range(7):
            c.drawCentredString(grid_x0 + col_w * d + col_w / 2, top - 8, t["days"][d])

        for i, room in enumerate(self.rooms):
            y_top = top - head_h - row_h * i
            if i % 2 == 0:
                c.setFillColor(STRIPE)
                c.rect(M, y_top - row_h, W - 2 * M, row_h, stroke=0, fill=1)
            c.setFillColor(INK)
            c.setFont("Helvetica-Bold", 10)
            c.drawString(M + 3, y_top - 14, room["name"])
            c.setFont("Helvetica", 8)
            c.setFillColor(MUTED)
            c.drawString(M + 3, y_top - 25, self.kind(room))
            c.drawString(M + 3, y_top - 35, f"{room['comfort']:.1f}° / {room['setback']:.1f}°")
            per_day = blocks_per_day(room)
            for d in range(7):
                x0 = grid_x0 + col_w * d + 2
                x1 = grid_x0 + col_w * (d + 1) - 2
                bar_y = y_top - row_h / 2 - 4
                self.timeline(x0, bar_y, x1, 9, per_day[d], labels=False)
                c.setFont("Helvetica", 7.5)
                c.setFillColor(INK)
                if per_day[d]:
                    for n, (s, e) in enumerate(per_day[d][:3]):
                        c.drawCentredString((x0 + x1) / 2, bar_y - 10 - 9 * n, f"{hhmm(s)}-{hhmm(e)}")
                else:
                    c.setFillColor(MUTED)
                    c.drawCentredString((x0 + x1) / 2, bar_y - 10, t["not_heated"])

        c.setFillColor(MUTED)
        c.setFont("Helvetica", 7.5)
        c.drawString(grid_x0, 14 * MM, t["axis_note"])
        self.next_page()

    def room_page(self, room: dict[str, Any]) -> None:
        c, t = self.c, self.t
        per_day = blocks_per_day(room)
        hours_week = sum(e - s for blocks in per_day.values() for s, e in blocks) / 60
        self.header(room["name"], t["room_sub"].format(kind=self.kind(room), hours=hours_week))
        self.legend(M, H - 30 * MM)

        y = H - 52 * MM
        cards = [
            (*t["card_comfort"], room["comfort"]),
            (*t["card_setback"], room["setback"]),
            (*t["card_frost"], room.get("frost_hold", 12)),
        ]
        card_w = 70 * MM
        for n, (title, note, value) in enumerate(cards):
            cx = M + n * (card_w + 8)
            c.setFillColor(colors.white)
            c.setStrokeColor(LINE)
            c.roundRect(cx, y, card_w, 34, 4, stroke=1, fill=1)
            c.setFillColor(MUTED)
            c.setFont("Helvetica", 8)
            c.drawString(cx + 8, y + 24, title.upper())
            c.setFillColor(COMFORT_DARK)
            c.setFont("Helvetica-Bold", 15)
            c.drawString(cx + 8, y + 8, f"{value:.1f}°C")
            c.setFillColor(MUTED)
            c.setFont("Helvetica", 7.5)
            c.drawRightString(cx + card_w - 8, y + 9, note)

        gx0 = M + 24 * MM
        gx1 = W - M - 30 * MM
        gtop = y - 20
        row = 27
        gbot = gtop - row * 7
        self.hour_grid(gx0, gbot, gx1, gtop + 4, label_y=gtop + 8)
        for d in range(7):
            ry = gtop - row * (d + 1) + 5
            c.setFillColor(INK)
            c.setFont("Helvetica-Bold", 10)
            c.drawString(M, ry + 7, t["days"][d])
            self.timeline(gx0, ry, gx1, 16, per_day[d], font=8.5)
            hours = sum(e - s for s, e in per_day[d]) / 60
            c.setFillColor(MUTED)
            c.setFont("Helvetica", 8)
            c.drawRightString(W - M, ry + 5, t["hours"].format(h=hours) if hours else t["off"])

        ny = gbot - 14
        c.setFillColor(ACCENT)
        c.setFont("Helvetica-Bold", 11)
        c.drawString(M, ny, t["discuss"])
        box_w = (W - 2 * M - 10) / 2
        for n, title in enumerate([t["box_left"], t["box_right"]]):
            bx = M + n * (box_w + 10)
            c.setFillColor(colors.white)
            c.setStrokeColor(LINE)
            c.roundRect(bx, 20 * MM, box_w, ny - 8 - 20 * MM, 4, stroke=1, fill=1)
            c.setFillColor(MUTED)
            c.setFont("Helvetica-Bold", 8.5)
            c.drawString(bx + 8, ny - 22, title)
            c.setStrokeColor(LINE)
            ly = ny - 40
            while ly > 20 * MM + 8:
                c.line(bx + 8, ly, bx + box_w - 8, ly)
                ly -= 18
        self.next_page()

    def observations(self) -> list[tuple[str, str]]:
        t = self.t
        points: list[tuple[str, str]] = []
        for room in self.rooms:
            per_day = blocks_per_day(room)
            off_days = [t["short"][d] for d in range(7) if not per_day[d]]
            if off_days and len(off_days) < 7:
                points.append((room["name"], t["no_comfort_days"].format(days=", ".join(off_days))))
            elif not any(per_day.values()):
                points.append((room["name"], t["no_schedule"]))

        day_rooms: dict[int, list[str]] = {}
        for room in self.rooms:
            per_day = blocks_per_day(room)
            for d in range(5):
                if any(s < 17 * 60 and e > 9 * 60 for s, e in per_day[d]):
                    day_rooms.setdefault(d, []).append(room["name"])
        for d in range(5):
            if not day_rooms.get(d):
                points.append((t["days"][d], t["nobody_daytime"]))
        if day_rooms:
            sample = "; ".join(f"{t['short'][d]}: {', '.join(day_rooms.get(d, [t['nobody']]))}" for d in range(5))
            points.append((t["daytime_title"], t["daytime_text"].format(sample=sample)))

        groups: dict[str, list[dict[str, Any]]] = {}
        for room in self.rooms:
            groups.setdefault(json.dumps(blocks_per_day(room), sort_keys=True), []).append(room)
        for group in groups.values():
            if len(group) > 1:
                temps = {(r["comfort"], r["setback"]) for r in group}
                extra = t["temps_differ"] if len(temps) > 1 else ""
                points.append((" + ".join(r["name"] for r in group), t["same_schedule"].format(extra=extra)))

        return points + list(t["static_points"])

    def talking_points(self) -> None:
        c, t = self.c, self.t
        self.header(t["points_title"], t["points_sub"])
        y = H - 36 * MM
        for title, text in self.observations():
            if y < 40:
                self.next_page()
                self.header(t["points_title"], t["points_more"])
                y = H - 36 * MM
            c.setFillColor(COMFORT)
            c.circle(M + 3, y + 3.5, 2.5, stroke=0, fill=1)
            c.setFillColor(INK)
            c.setFont("Helvetica-Bold", 10.5)
            c.drawString(M + 12, y, title)
            c.setFillColor(MUTED)
            line, ty = "", y - 13
            for word in text.split():
                trial = f"{line} {word}".strip()
                if c.stringWidth(trial, "Helvetica", 10) > W - 2 * M - 14:
                    c.setFont("Helvetica", 10)
                    c.drawString(M + 12, ty, line)
                    ty -= 12
                    line = word
                else:
                    line = trial
            c.setFont("Helvetica", 10)
            c.drawString(M + 12, ty, line)
            y = ty - 20
        self.footer()

    def build(self) -> None:
        self.overview()
        for room in self.rooms:
            self.room_page(room)
        self.talking_points()
        self.c.save()


def load_rooms(source: Path) -> list[dict[str, Any]]:
    raw = json.loads(source.read_text(encoding="utf-8"))
    rooms = raw["data"]["options"]["rooms"]
    if not rooms:
        raise SystemExit("The export contains no rooms.")
    return rooms


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("export", type=Path, help="diagnostics JSON of the Smart Heating config entry")
    parser.add_argument("output", type=Path, help="PDF file to write")
    parser.add_argument("--lang", choices=sorted(TEXTS), default="en", help="language of the PDF (default: en)")
    args = parser.parse_args()
    Report(load_rooms(args.export), args.output, args.lang).build()
    print(f"Saved {args.output}")


if __name__ == "__main__":
    main()
