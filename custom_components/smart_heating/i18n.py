"""Pure translations of the texts Smart Heating generates itself (English and Dutch).

The options flow uses Home Assistant's own translation files (strings.json,
translations/*.json); everything else (sentences on cards, alerts, the dashboard,
advice and the digest, entity names) comes from here. No Home Assistant imports.
"""

from __future__ import annotations

from typing import Any

DEFAULT_LANGUAGE = "en"
LANGUAGES = ("en", "nl")


def pick_language(code: str | None) -> str:
    """Our language for a Home Assistant language code such as 'nl' or 'nl-NL'."""
    base = (code or "").lower().replace("_", "-").split("-")[0]
    return base if base in LANGUAGES else DEFAULT_LANGUAGE


def number(value: float, lang: str = DEFAULT_LANGUAGE) -> str:
    """19.5 as '19.5' (en) or '19,5' (nl); whole numbers without decimals."""
    text = f"{value:g}"
    return text.replace(".", ",") if lang == "nl" else text


def tr(lang: str, key: str, **params: Any) -> str:
    """The text for `key` in `lang`, English when missing, the key itself as last resort."""
    text = CATALOG.get(lang, {}).get(key)
    if text is None:
        text = CATALOG[DEFAULT_LANGUAGE].get(key, key)
    return text.format(**params) if params else text


WEEKDAYS = {
    "en": ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"),
    "nl": ("ma", "di", "wo", "do", "vr", "za", "zo"),
}


def weekday(lang: str, index: int) -> str:
    return WEEKDAYS.get(lang, WEEKDAYS[DEFAULT_LANGUAGE])[index]


HELP: dict[str, list[tuple[str, str]]] = {
    "en": [
        (
            "Overview",
            "Top line: which rooms heat and whether the boiler is on. Each room shows its "
            "temperature now, what it aims for and what it is doing. Alerts only appear when "
            "something needs attention.\n\nA room can heat while the boiler is off: only rooms "
            "that should be warm call the boiler.",
        ),
        (
            "Room sentences: schedule and boost",
            "| You see | Meaning |\n|---|---|\n"
            "| Warm until 17:00 | In a scheduled warm period. |\n"
            "| Warm from 08:00 | Lower temperature now, warms up for the next period. |\n"
            "| Kept at 16 degrees | Lower temperature, nothing scheduled. |\n"
            "| Warming up, warm until 17:00 | Started early so it is warm when the schedule begins. |\n"
            "| Boost until 14:00 | You pressed Boost. Warm until then or until you cancel. |",
        ),
        (
            "Room sentences: away and vacation",
            "| You see | Meaning |\n|---|---|\n"
            "| Nobody home, kept at 16 degrees | Nobody is home. Long absence: just above freezing. |\n"
            "| Room's person is away, kept at 16 degrees | The person this room is for is away: schedule skipped. Warms up when they are back or on their way. |\n"
            "| Vacation until Sat 16:20, kept at 12 degrees | Vacation mode: just above freezing. Each room starts warming up in time for your return. |\n"
            "| Waiting for the floor heating to warm up first, kept at 12 degrees | The slow floor heating warms up first. Idle radiators stay closed meanwhile. |",
        ),
        (
            "Room sentences: window, sensor and manual",
            "| You see | Meaning |\n|---|---|\n"
            "| Window seems open, heating paused until 14:20 | It cooled faster than usual for this room, so heating pauses a while. |\n"
            "| Reached 19.5 degrees, radiator closed | The room sensor reads the target or higher, so the radiator is shut even if the valve's own sensor disagrees. Opens again when the room cools a little. A room without a room sensor never shows this: its valve closes itself and the sentence keeps showing the schedule. |\n"
            "| Set by hand to 22 degrees, until 17:00 | You turned the valve yourself. Left alone until the room's target changes. The boiler is called if the room is colder than you set. |\n\n"
            "Strongest rule wins: Boost, open window, Vacation, nobody home, schedule.",
        ),
        (
            "Heating page",
            "- **Right now / Next change**: what the room does and when that changes.\n"
            "- **Pre-heat lead time**: how early the room starts warming up. A fixed guess at first, "
            "then learned per room.\n"
            "- **Boost / Cancel boost**: warm the room now for a set time, or stop early.\n"
            "- **Radiator valve**: battery and valve details.",
        ),
        (
            "Boiler page",
            "- **Boiler is being called**: only when a room that should be warm is clearly too cold.\n"
            "- **Rooms asking for heat**: who caused the call.\n"
            "- **Target we set / Last sent / Result**: what we told the boiler thermostat, when, and if it worked.\n"
            "- **Paused after an error**: a short wait so the thermostat (or its cloud) is not flooded.\n"
            "- **Manual change on the boiler thermostat**: you changed it yourself. Respected for about two hours.\n"
            "- **Manual room override**: for rooms you heat by hand. Calls the boiler for a set time. Cancel to stop early.",
        ),
        (
            "Rooms without smart valves",
            "A room set up with **open radiators** has no smart valve yet. It calls the boiler when it "
            "is cold and **stops every boiler call once it is at its comfort temperature**, so the "
            "house does not get warmer than that room should be. A cold room elsewhere then waits. "
            "The Manual room override still starts the boiler.",
        ),
        (
            "Vacation and coming home",
            "**Vacation**: pick when you are back (*Back from vacation*) and turn on *Vacation mode*, "
            "or put an event such as \"Vacation\" in the vacation calendar set in the options: it "
            "switches on and off by itself. The house holds frost protection; each room starts "
            "warming up just in time for your return.\n\n"
            "**Coming home**: when a phone with the Home Assistant app is on its way home, the house "
            "starts warming up so it is comfortable when you arrive. No zones to draw.",
        ),
        (
            "What the system learns",
            "Per room, kept across restarts, standard values until there is data:\n"
            "- **Pre-heat time**: how fast each room warms up, so it starts early enough for how cold it is now.\n"
            "- **Open window**: what a normal temperature change is, so a window is spotted sooner.\n"
            "- **Coast**: how far a room keeps warming after the boiler stops, so the boiler stops earlier.\n"
            "- **Thermometers**: the difference between the valve's and the room's thermometer.\n"
            "- **Your habits**: Boost or valve turned up at the same time on 3+ days shows up as a "
            "piece of advice under Settings > Repairs. The schedule is never changed by itself.",
        ),
        (
            "Changed something by hand?",
            "A radiator you turn by hand is left alone until that room's target next changes.",
        ),
    ],
    "nl": [
        (
            "Overzicht",
            "Bovenste regel: welke ruimtes verwarmen en of de boiler aan staat. Elke ruimte toont "
            "de temperatuur nu, het doel en wat ze doet. Meldingen verschijnen alleen als er "
            "aandacht nodig is.\n\nEen ruimte kan verwarmen terwijl de boiler uit staat: alleen "
            "ruimtes die warm moeten zijn vragen de boiler om warmte.",
        ),
        (
            "Zinnen: schema en boost",
            "| Je ziet | Betekenis |\n|---|---|\n"
            "| Warm tot 17:00 | In een geplande warme periode. |\n"
            "| Warm vanaf 08:00 | Nu lagere temperatuur, warmt op voor de volgende periode. |\n"
            "| Op 16 graden gehouden | Lagere temperatuur, niets gepland. |\n"
            "| Opwarmen, warm tot 17:00 | Eerder begonnen, zodat het warm is als het schema start. |\n"
            "| Boost tot 14:00 | Je drukte op Boost. Warm tot dan of tot je annuleert. |",
        ),
        (
            "Zinnen: weg en vakantie",
            "| Je ziet | Betekenis |\n|---|---|\n"
            "| Niemand thuis, op 16 graden gehouden | Niemand is thuis. Lange afwezigheid: net boven vorst. |\n"
            "| Persoon van deze ruimte is weg, op 16 graden gehouden | De persoon voor wie deze ruimte is, is weg: schema overgeslagen. Warmt op als diegene terug of onderweg is. |\n"
            "| Vakantie tot za 16:20, op 12 graden gehouden | Vakantiemodus: net boven vorst. Elke ruimte begint op tijd op te warmen voor je terugkomst. |\n"
            "| Wacht tot de vloerverwarming is opgewarmd, op 12 graden gehouden | De trage vloerverwarming warmt eerst op. Ongebruikte radiatoren blijven intussen dicht. |",
        ),
        (
            "Zinnen: raam, sensor en handmatig",
            "| Je ziet | Betekenis |\n|---|---|\n"
            "| Raam lijkt open, verwarming gepauzeerd tot 14:20 | Koelde sneller af dan normaal voor deze ruimte, dus de verwarming pauzeert even. |\n"
            "| 19,5 graden bereikt, radiator dicht | De kamersensor meldt de doeltemperatuur of meer, dus de radiator gaat dicht, ook als de eigen sensor van de kraan het anders ziet. Gaat weer open als de kamer iets afkoelt. Een kamer zonder kamersensor toont dit nooit: de kraan sluit zelf en de zin blijft het schema tonen. |\n"
            "| Handmatig ingesteld op 22 graden, tot 17:00 | Je draaide de kraan zelf. Met rust gelaten tot het doel van de ruimte verandert. De boiler wordt gevraagd als de ruimte kouder is dan jouw instelling. |\n\n"
            "Sterkste regel wint: Boost, open raam, Vakantie, niemand thuis, schema.",
        ),
        (
            "Pagina Verwarming",
            "- **Nu / Volgende wijziging**: wat de ruimte doet en wanneer dat verandert.\n"
            "- **Voorverwarmtijd**: hoe vroeg de ruimte begint op te warmen. Eerst een vaste schatting, "
            "daarna per ruimte geleerd.\n"
            "- **Boost / Boost annuleren**: warm de ruimte nu een ingestelde tijd op, of stop eerder.\n"
            "- **Radiatorkraan**: batterij en kraandetails.",
        ),
        (
            "Pagina Boiler",
            "- **Boiler wordt aangeroepen**: alleen als een ruimte die warm moet zijn duidelijk te koud is.\n"
            "- **Ruimtes die warmte vragen**: wie de aanvraag veroorzaakte.\n"
            "- **Doel / Laatst verstuurd / Resultaat**: wat we de ketelthermostaat opdroegen, wanneer, en of het lukte.\n"
            "- **Gepauzeerd na een fout**: even wachten zodat de thermostaat (of zijn cloud) niet overspoeld wordt.\n"
            "- **Handmatige wijziging op de ketelthermostaat**: je veranderde het zelf. Ongeveer twee uur gerespecteerd.\n"
            "- **Handmatige ruimte-override**: voor ruimtes die je met de hand verwarmt. Roept de boiler een ingestelde tijd aan. Annuleer om eerder te stoppen.",
        ),
        (
            "Ruimtes zonder slimme kranen",
            "Een ruimte met **open radiatoren** heeft nog geen slimme kraan. Ze vraagt de boiler om "
            "warmte als het koud is en **stopt elke boileraanvraag zodra ze op comforttemperatuur is**, "
            "zodat het huis niet warmer wordt dan die ruimte hoort te zijn. Een koude ruimte elders "
            "wacht dan. De Handmatige ruimte-override zet de boiler wel aan.",
        ),
        (
            "Vakantie en thuiskomen",
            "**Vakantie**: kies wanneer je terug bent (*Terug van vakantie*) en zet *Vakantiemodus* "
            "aan, of zet een afspraak zoals \"Vakantie\" in de vakantieagenda uit de opties: die gaat "
            "dan vanzelf aan en uit. Het huis blijft op vorstbescherming; elke ruimte begint precies "
            "op tijd op te warmen voor je terugkomst.\n\n"
            "**Thuiskomen**: als een telefoon met de Home Assistant-app onderweg naar huis is, begint "
            "het huis op te warmen zodat het aangenaam is als je aankomt. Geen zones nodig.",
        ),
        (
            "Wat het systeem leert",
            "Per ruimte, bewaard na een herstart, standaardwaarden tot er gegevens zijn:\n"
            "- **Voorverwarmtijd**: hoe snel elke ruimte opwarmt, zodat hij vroeg genoeg begint voor hoe koud hij nu is.\n"
            "- **Open raam**: wat een normale temperatuurwijziging is, zodat een raam sneller opvalt.\n"
            "- **Nawarmen**: hoever een ruimte blijft opwarmen nadat de boiler stopt, zodat de boiler eerder stopt.\n"
            "- **Thermometers**: het verschil tussen de thermometer van de kraan en die van de ruimte.\n"
            "- **Jouw gewoontes**: Boost of kraan hoger op dezelfde tijd op 3+ dagen komt als "
            "advies onder Instellingen > Reparaties. Het schema verandert nooit vanzelf.",
        ),
        (
            "Zelf iets versteld?",
            "Een radiator die je met de hand verstelt, wordt met rust gelaten tot het doel van die ruimte weer verandert.",
        ),
    ],
}


def help_cards(lang: str) -> list[tuple[str, str]]:
    return HELP.get(lang, HELP[DEFAULT_LANGUAGE])


CATALOG: dict[str, dict[str, str]] = {
    "en": {
        # status line and boiler card
        "status.heating": "Heating: {rooms}.",
        "status.nothing": "Nothing is heating.",
        "status.boiler_on": "Boiler on.",
        "status.boiler_off": "Boiler off.",
        "status.vacation": "Vacation mode is on.",
        "status.away": "Nobody is home.",
        "demand.none": "None",
        "demand.manual_override": "Manual room override",
        "backoff.no": "No",
        "backoff.waiting": "Waiting until {at}",
        "hold.no": "No",
        "hold.respecting": "Respecting a manual change until {at}",
        # alerts
        "alert.a_room": "a room",
        "diagnosis.boiler_outage.title": "Boiler thermostat unreachable",
        "diagnosis.boiler_outage": "The boiler thermostat cannot be reached, so the boiler cannot be called reliably. The radiator valves keep following the schedule. Check that the thermostat has power and a connection.",
        "diagnosis.frost_risk.title": "{room}: frost risk",
        "diagnosis.frost_risk": "{room} is close to freezing protection and is not warming up. Close windows and doors, open the radiator valve and check that the radiator gets warm.",
        "diagnosis.valve_unreachable.title": "{room}: radiator valve not responding",
        "diagnosis.valve_unreachable": "The radiator valve in {room} is not responding. Replace its batteries, then move it closer to the network or add a powered device in between.",
        "diagnosis.valve_off.title": "{room}: radiator valve stays off",
        "diagnosis.valve_off": "The radiator valve in {room} is switched off and does not turn back on. Check the valve itself for a child lock or an error, and replace its batteries.",
        "diagnosis.valve_rejects.title": "{room}: radiator valve ignores settings",
        "diagnosis.valve_rejects": "The radiator valve in {room} does not accept its temperature. Replace the batteries; if that does not help, remount and recalibrate the valve or replace it.",
        "diagnosis.no_heat.title": "{room}: asks for heat but stays cold",
        "diagnosis.no_heat": "{room} asks for heat but barely warms up. Check for an open window or door, feel whether the radiator gets warm (bleed it, check the valve pin) and whether something covers it. Until it warms up it only asks the boiler for heat every few hours.",
        "diagnosis.too_cold.title": "{room}: stays too cold",
        "diagnosis.too_cold": "{room} has been too cold for a long time. Check windows and doors and whether the radiator gets warm. If it does, the target may be higher than this radiator can reach.",
        "diagnosis.battery.title": "{room}: battery low",
        "diagnosis.battery": "The battery of the radiator valve in {room} is low. Replace it soon.",
        "diagnosis.sensor.title": "{room}: temperature sensor silent",
        "diagnosis.sensor": "The temperature sensor in {room} stopped reporting. Replace its battery or check its connection. Until then the radiator valve's own sensor is used.",
        "advice.fault.count": "Seen on {count} days in the last four weeks.",
        "advice.probably": "Probably (judged by the sensor on the radiator valve):",
        "advice.leak.title": "{room}: radiator heats while it should be closed",
        "advice.leak": "{room} warmed up {count} times in four weeks while its radiator should have been closed and other rooms used the boiler. Check that the valve is mounted tightly and calibrate it, replace its batteries, and make sure the temperature sensor is not near a heat source.",
        "advice.leak.sun": "It only happened in daytime, so sunshine may be the cause.",
        "advice.sole_caller.title": "{room} keeps the boiler on by itself",
        "advice.sole_caller": "{room} alone kept the boiler on for {hours} hours a week. Consider starting its schedule later, ending it earlier or lowering its comfort temperature, and check for draughts.",
        "advice.long_preheat.title": "{room}: very long pre-heat",
        "advice.long_preheat": "{room} pre-heated for about {preheat} hours on {count} days. A smaller difference between setback and comfort, or a longer comfort period, is usually cheaper than a long climb.",
        "advice.late.title": "{room} is not warm on time",
        "advice.late": "{room} was still cold at the start of a warm period on {count} days. Raise the setback temperature a little or check the radiator.",
        "advice.add_sensor.title": "{room}: add a room sensor",
        "advice.add_sensor": "{room} has no room sensor, so its temperature comes from the radiator valve. A sensor away from the radiator saves gas and makes better advice possible.",
        "advice.trim_schedule.title": "{room}: shorten the schedule",
        "advice.trim_schedule": "{room}: on {days} the warm period {old} was often partly for nobody (people away or the valve turned down). Proposal: {what}.",
        "advice.trim.drop": "skip it on those days",
        "advice.trim.change": "make it {start}–{end}",
        "advice.add_time.title": "{room}: add a warm period",
        "advice.add_time": "You often ask for heat in {room} on {days} around {time} ({count} times in four weeks). Add it to the schedule so the room is warm on time.",
        "advice.occupants.title": "{room}: link its people",
        "advice.occupants": "The valve in {room} is mostly turned down while {people} is away. Link the room to its people and its schedule is skipped while they are all away.",
        "advice.saving": "Saves up to about {hours} boiler hours a week.",
        "advice.saving_cost": "Saves up to about {hours} boiler hours (about {cost} {currency}) a week.",
        "digest.title": "Smart Heating this week",
        "digest.same": "You used about as much gas as in the same week last year, weather taken into account.",
        "digest.less": "You used {pct}% less gas than in the same week last year, weather taken into account.",
        "digest.more": "You used {pct}% more gas than in the same week last year, weather taken into account.",
        "digest.actions": "What you can do (details under Settings > Repairs):",
        "digest.effects": "Effect of earlier changes:",
        "digest.effect": "- {room}: boiler hours it caused alone went from {before} to {after} a week.",
        "digest.push_actions": "{count} things you can do, see Home Assistant.",
        "dash.advice": "Advice",
        "entity.advice": "Smart Heating advice",
        "entity.undo_advice": "Undo last advice change",
        "alert.resolved": "Resolved: {text}",
        # room sentences
        "degrees": "{value} degrees",
        "summary.boost": "Boost until {end}",
        "summary.boost_open": "Boost",
        "summary.window": "Window seems open, heating paused until {end}",
        "summary.window_open": "Window seems open",
        "summary.vacation": "Vacation until {end}, kept at {temp}",
        "summary.vacation_open": "Vacation, kept at {temp}",
        "summary.away": "Nobody home, kept at {temp}",
        "summary.occupant_away": "Room's person is away, kept at {temp}",
        "summary.satisfied": "Reached {temp}, radiator closed",
        "summary.floor_first": "Waiting for the floor heating to warm up first, kept at {temp}",
        "summary.manual": "Set by hand to {temp}, until {end}",
        "summary.manual_open": "Set by hand to {temp}",
        "summary.pre_heat": "Warming up, warm until {end}",
        "summary.pre_heat_open": "Warming up",
        "summary.schedule": "Warm until {end}",
        "summary.schedule_open": "Warm",
        "summary.setback": "Warm from {end}",
        "summary.setback_open": "Kept at {temp}",
        # entity names
        "entity.reason": "{room} heating reason",
        "entity.summary": "{room} summary",
        "entity.next_change": "{room} next change",
        "entity.lead_time": "{room} pre-heat lead time",
        "entity.boost": "{room} boost",
        "entity.cancel_boost": "{room} cancel boost",
        "entity.thermometer": "{room} thermometer reading",
        "calibration.title": "Smart Heating calibration",
        "calibration.ask_cold": "The radiator in {room} is cold now. Read a thermometer in the room, away from the radiator, and enter it at '{room} thermometer reading'.",
        "calibration.ask_heating": "The radiator in {room} is hot now. Read a thermometer in the room, away from the radiator, and enter it at '{room} thermometer reading'.",
        "entity.manual_override": "Manual room override",
        "entity.cancel_manual_override": "Cancel manual room override",
        "entity.cancel_boiler_hold": "End manual change on the boiler thermostat",
        "entity.status": "Smart Heating status",
        "entity.active_alerts": "Smart Heating active alerts",
        "entity.boiler_demand_rooms": "Smart Heating boiler demand from",
        "entity.boiler_target": "Smart Heating boiler target",
        "entity.boiler_last_write": "Smart Heating boiler last write",
        "entity.boiler_write_result": "Smart Heating boiler last write result",
        "entity.boiler_backoff": "Smart Heating boiler backoff",
        "entity.boiler_manual_hold": "Smart Heating boiler manual hold",
        "entity.boiler_call": "Smart Heating boiler called",
        "entity.vacation_return": "Back from vacation",
        "entity.vacation_mode": "Vacation mode",
        "entity.alerts_unit": "alerts",
        "climate.set_refused": (
            "This target is set by Smart Heating (schedule, Boost, Away, Vacation). "
            "Use Boost, or edit the room's temperatures under Configure."
        ),
        # dashboard
        "dash.title": "Smart Heating",
        "dash.view.overview": "Overview",
        "dash.view.heating": "Heating",
        "dash.view.schedule": "Schedule",
        "dash.schedule.temps": "Warm at {comfort}°, otherwise kept at {setback}°.",
        "dash.schedule.days": "Days",
        "dash.schedule.warm": "Warm",
        "dash.schedule.none": "–",
        "dash.schedule.hint": (
            "Shows the schedule only. Boost, vacation, nobody home and an open window override it, "
            "and each room starts warming up a little before its warm time. Edit under Configure."
        ),
        "dash.view.boiler": "Boiler",
        "dash.view.help": "Help",
        "dash.right_now": "Right now",
        "dash.alerts": "Alerts",
        "dash.controls": "Controls",
        "dash.boiler": "Boiler",
        "dash.last_24h": "Last 24 hours",
        "dash.manual_override": "Manual room override",
        "dash.help_title": "How to read this",
        "dash.next_change": "Next change",
        "dash.lead_time": "Pre-heat lead time",
        "dash.boost": "Boost",
        "dash.cancel_boost": "Cancel boost",
        "dash.radiator_valve": "Radiator valve",
        "dash.battery": "Battery",
        "dash.valve_opening": "Valve opening",
        "dash.valve_demand": "Valve heating demand",
        "dash.boiler_called": "Boiler is being called",
        "dash.demand_rooms": "Rooms asking for heat",
        "dash.target": "Target we set on the boiler thermostat",
        "dash.last_sent": "Last sent to the boiler thermostat",
        "dash.write_result": "Result of last send",
        "dash.paused": "Paused after an error",
        "dash.manual_hold": "Manual change on the boiler thermostat",
        "dash.table.room": "Room",
        "dash.table.now": "Now",
        "dash.table.aiming": "Aiming for",
        "dash.table.what": "What is happening",
        "dash.options_hint": (
            "Edit schedules, comfort and setback per room under "
            "[Smart Heating options]({link}) (Configure, Edit a room)."
        ),
        "dash.header_alerts": (
            "{% if n > 0 %}**{{ n }} alert{{ 's' if n != 1 }}** need attention, see Alerts below."
            "{% else %}No alerts.{% endif %}"
        ),
        # room form errors
        "room_error.invalid_time": "invalid time {text}",
        "room_error.invalid_days": "invalid days {text}",
        "room_error.invalid_line": "invalid schedule line {text}",
        "room_error.empty_window": "empty window in {text}",
        "room_error.name_required": "name is required",
        "room_error.name_needs_letters": "the name needs at least one letter or digit",
        "room_error.floor_needs_sensor": "a floor heating or open-radiator room needs a temperature sensor",
        "room_error.trv_required": "trv entity is required (or mark the room as manual)",
        "room_error.comfort_range": "comfort must be {low}-{high}",
        "room_error.frost_min": "frost hold must be at least {low}",
        "room_error.temp_order": "need frost hold <= setback <= comfort",
        "room_error.out_of_range": "{key} must be {low}-{high}",
        "room_error.duplicate_name": "a room with that name (or one that only differs in case or punctuation) already exists",
        "room_error.duplicate_trv": "that trv entity is already used by another room",
        "room_error.unknown_room": "unknown room {text}",
    },
    "nl": {
        "status.heating": "Verwarmen: {rooms}.",
        "status.nothing": "Er wordt niets verwarmd.",
        "status.boiler_on": "Boiler aan.",
        "status.boiler_off": "Boiler uit.",
        "status.vacation": "Vakantiemodus staat aan.",
        "status.away": "Niemand is thuis.",
        "demand.none": "Geen",
        "demand.manual_override": "Handmatige ruimte-override",
        "backoff.no": "Nee",
        "backoff.waiting": "Wacht tot {at}",
        "hold.no": "Nee",
        "hold.respecting": "Handmatige wijziging gerespecteerd tot {at}",
        "alert.a_room": "een ruimte",
        "diagnosis.boiler_outage.title": "Ketelthermostaat onbereikbaar",
        "diagnosis.boiler_outage": "De ketelthermostaat is onbereikbaar, dus de boiler kan niet betrouwbaar worden aangeroepen. De radiatorkranen blijven het schema volgen. Controleer of de thermostaat stroom en verbinding heeft.",
        "diagnosis.frost_risk.title": "{room}: kans op bevriezing",
        "diagnosis.frost_risk": "{room} zit vlak bij de vorstbescherming en warmt niet op. Sluit ramen en deuren, controleer de radiatorkraan en voel of de radiator warm wordt.",
        "diagnosis.valve_unreachable.title": "{room}: radiatorkraan reageert niet",
        "diagnosis.valve_unreachable": "De radiatorkraan in {room} reageert niet. Vervang de batterijen, en verbeter daarna het bereik met een apparaat op netstroom in de buurt.",
        "diagnosis.valve_off.title": "{room}: radiatorkraan blijft uit",
        "diagnosis.valve_off": "De radiatorkraan in {room} staat uit en gaat niet weer aan. Kijk op de kraan naar een kinderslot of foutmelding en vervang de batterijen.",
        "diagnosis.valve_rejects.title": "{room}: radiatorkraan neemt niets aan",
        "diagnosis.valve_rejects": "De radiatorkraan in {room} neemt zijn temperatuur niet over. Vervang de batterijen; helpt dat niet, monteer en kalibreer de kraan opnieuw of vervang hem.",
        "diagnosis.no_heat.title": "{room}: vraagt warmte maar blijft koud",
        "diagnosis.no_heat": "{room} vraagt om warmte maar warmt nauwelijks op. Controleer op een open raam of deur, voel of de radiator warm wordt (ontlucht hem, controleer de kraanpen) en of er iets voor staat. Tot de ruimte opwarmt wordt de ketel er maar om de paar uur voor aangezet.",
        "diagnosis.too_cold.title": "{room}: blijft te koud",
        "diagnosis.too_cold": "{room} is al lange tijd te koud. Controleer ramen en deuren en of de radiator warm wordt. Is dat zo, dan is het doel misschien hoger dan deze radiator haalt.",
        "diagnosis.battery.title": "{room}: batterij bijna leeg",
        "diagnosis.battery": "De batterij van de radiatorkraan in {room} is bijna leeg. Vervang hem binnenkort.",
        "diagnosis.sensor.title": "{room}: temperatuursensor is stil",
        "diagnosis.sensor": "De temperatuursensor in {room} meldt niets meer. Vervang de batterij of controleer de verbinding. Tot die tijd wordt de sensor van de radiatorkraan gebruikt.",
        "advice.fault.count": "Gezien op {count} dagen in de afgelopen vier weken.",
        "advice.probably": "Waarschijnlijk (beoordeeld met de sensor op de radiatorkraan):",
        "advice.leak.title": "{room}: radiator warmt terwijl hij dicht hoort",
        "advice.leak": "{room} warmde in vier weken {count} keer op terwijl de radiator dicht hoorde en andere ruimtes de ketel gebruikten. Controleer of de kraan goed vastzit en kalibreer hem, vervang de batterijen en zorg dat de temperatuursensor niet bij een warmtebron zit.",
        "advice.leak.sun": "Het gebeurde alleen overdag, dus de zon kan de oorzaak zijn.",
        "advice.sole_caller.title": "{room} houdt in zijn eentje de ketel aan",
        "advice.sole_caller": "{room} hield in zijn eentje de ketel {hours} uur per week aan. Overweeg het schema later te laten beginnen of eerder te laten stoppen, of de comforttemperatuur te verlagen, en controleer op tocht.",
        "advice.long_preheat.title": "{room}: erg lang voorverwarmen",
        "advice.long_preheat": "{room} verwarmde op {count} dagen ongeveer {preheat} uur voor. Een kleiner verschil tussen verlaagde en comforttemperatuur, of een langere warme periode, is meestal zuiniger dan een lange opwarming.",
        "advice.late.title": "{room} is niet op tijd warm",
        "advice.late": "{room} was op {count} dagen nog koud aan het begin van een warme periode. Verhoog de verlaagde temperatuur iets of controleer de radiator.",
        "advice.add_sensor.title": "{room}: voeg een ruimtesensor toe",
        "advice.add_sensor": "{room} heeft geen ruimtesensor, dus de temperatuur komt van de radiatorkraan. Een sensor weg van de radiator bespaart gas en maakt beter advies mogelijk.",
        "advice.trim_schedule.title": "{room}: schema inkorten",
        "advice.trim_schedule": "{room}: op {days} was de warme periode {old} vaak deels voor niemand (mensen weg of kraan lager gedraaid). Voorstel: {what}.",
        "advice.trim.drop": "op die dagen overslaan",
        "advice.trim.change": "maak er {start}–{end} van",
        "advice.add_time.title": "{room}: warme periode toevoegen",
        "advice.add_time": "Je vraagt in {room} vaak om warmte op {days} rond {time} ({count} keer in vier weken). Zet het in het schema, dan is de ruimte op tijd warm.",
        "advice.occupants.title": "{room}: koppel de personen",
        "advice.occupants": "De kraan in {room} wordt vooral lager gedraaid als {people} weg is. Koppel de ruimte aan haar personen, dan wordt het schema overgeslagen als ze allemaal weg zijn.",
        "advice.saving": "Bespaart tot ongeveer {hours} keteluren per week.",
        "advice.saving_cost": "Bespaart tot ongeveer {hours} keteluren (ongeveer {cost} {currency}) per week.",
        "digest.title": "Smart Heating deze week",
        "digest.same": "Je verbruikte ongeveer evenveel gas als in dezelfde week vorig jaar, rekening houdend met het weer.",
        "digest.less": "Je verbruikte {pct}% minder gas dan in dezelfde week vorig jaar, rekening houdend met het weer.",
        "digest.more": "Je verbruikte {pct}% meer gas dan in dezelfde week vorig jaar, rekening houdend met het weer.",
        "digest.actions": "Wat je kunt doen (details onder Instellingen > Reparaties):",
        "digest.effects": "Effect van eerdere aanpassingen:",
        "digest.effect": "- {room}: de keteluren die de ruimte alleen veroorzaakte gingen van {before} naar {after} per week.",
        "digest.push_actions": "{count} dingen die je kunt doen, zie Home Assistant.",
        "dash.advice": "Advies",
        "entity.advice": "Smart Heating adviezen",
        "entity.undo_advice": "Laatste adviesaanpassing ongedaan maken",
        "alert.resolved": "Opgelost: {text}",
        "degrees": "{value} graden",
        "summary.boost": "Boost tot {end}",
        "summary.boost_open": "Boost",
        "summary.window": "Raam lijkt open, verwarming gepauzeerd tot {end}",
        "summary.window_open": "Raam lijkt open",
        "summary.vacation": "Vakantie tot {end}, op {temp} gehouden",
        "summary.vacation_open": "Vakantie, op {temp} gehouden",
        "summary.away": "Niemand thuis, op {temp} gehouden",
        "summary.occupant_away": "Persoon van deze ruimte is weg, op {temp} gehouden",
        "summary.satisfied": "{temp} bereikt, radiator dicht",
        "summary.floor_first": "Wacht tot de vloerverwarming is opgewarmd, op {temp} gehouden",
        "summary.manual": "Handmatig ingesteld op {temp}, tot {end}",
        "summary.manual_open": "Handmatig ingesteld op {temp}",
        "summary.pre_heat": "Opwarmen, warm tot {end}",
        "summary.pre_heat_open": "Opwarmen",
        "summary.schedule": "Warm tot {end}",
        "summary.schedule_open": "Warm",
        "summary.setback": "Warm vanaf {end}",
        "summary.setback_open": "Op {temp} gehouden",
        "entity.reason": "{room} verwarmingsreden",
        "entity.summary": "{room} samenvatting",
        "entity.next_change": "{room} volgende wijziging",
        "entity.lead_time": "{room} voorverwarmtijd",
        "entity.boost": "{room} boost",
        "entity.cancel_boost": "{room} boost annuleren",
        "entity.thermometer": "{room} thermometerwaarde",
        "calibration.title": "Smart Heating ijken",
        "calibration.ask_cold": "De radiator in {room} is nu koud. Lees een thermometer in de ruimte af, niet bij de radiator, en vul de waarde in bij '{room} thermometerwaarde'.",
        "calibration.ask_heating": "De radiator in {room} is nu warm. Lees een thermometer in de ruimte af, niet bij de radiator, en vul de waarde in bij '{room} thermometerwaarde'.",
        "entity.manual_override": "Handmatige ruimte-override",
        "entity.cancel_manual_override": "Handmatige ruimte-override annuleren",
        "entity.cancel_boiler_hold": "Handmatige wijziging op de ketelthermostaat beëindigen",
        "entity.status": "Smart Heating status",
        "entity.active_alerts": "Smart Heating actieve meldingen",
        "entity.boiler_demand_rooms": "Smart Heating boiler-aanvraag van",
        "entity.boiler_target": "Smart Heating boilerdoel",
        "entity.boiler_last_write": "Smart Heating boiler laatst verstuurd",
        "entity.boiler_write_result": "Smart Heating boiler resultaat laatste verzending",
        "entity.boiler_backoff": "Smart Heating boiler pauze",
        "entity.boiler_manual_hold": "Smart Heating boiler handmatige wijziging",
        "entity.boiler_call": "Smart Heating boiler aangeroepen",
        "entity.vacation_return": "Terug van vakantie",
        "entity.vacation_mode": "Vakantiemodus",
        "entity.alerts_unit": "meldingen",
        "climate.set_refused": (
            "Dit doel wordt bepaald door Smart Heating (schema, Boost, Afwezig, Vakantie). "
            "Gebruik Boost, of pas de temperaturen van de ruimte aan onder Configureren."
        ),
        "dash.title": "Smart Heating",
        "dash.view.overview": "Overzicht",
        "dash.view.heating": "Verwarming",
        "dash.view.schedule": "Schema",
        "dash.schedule.temps": "Warm op {comfort}°, anders op {setback}° gehouden.",
        "dash.schedule.days": "Dagen",
        "dash.schedule.warm": "Warm",
        "dash.schedule.none": "–",
        "dash.schedule.hint": (
            "Toont alleen het schema. Boost, vakantie, niemand thuis en een open raam gaan voor, "
            "en elke ruimte begint iets eerder op te warmen. Aanpassen onder Configureren."
        ),
        "dash.view.boiler": "Boiler",
        "dash.view.help": "Help",
        "dash.right_now": "Nu",
        "dash.alerts": "Meldingen",
        "dash.controls": "Bediening",
        "dash.boiler": "Boiler",
        "dash.last_24h": "Laatste 24 uur",
        "dash.manual_override": "Handmatige ruimte-override",
        "dash.help_title": "Zo lees je dit",
        "dash.next_change": "Volgende wijziging",
        "dash.lead_time": "Voorverwarmtijd",
        "dash.boost": "Boost",
        "dash.cancel_boost": "Boost annuleren",
        "dash.radiator_valve": "Radiatorkraan",
        "dash.battery": "Batterij",
        "dash.valve_opening": "Kraanstand",
        "dash.valve_demand": "Warmtevraag van de kraan",
        "dash.boiler_called": "Boiler wordt aangeroepen",
        "dash.demand_rooms": "Ruimtes die warmte vragen",
        "dash.target": "Doel dat we op de ketelthermostaat hebben gezet",
        "dash.last_sent": "Laatst naar de ketelthermostaat gestuurd",
        "dash.write_result": "Resultaat laatste verzending",
        "dash.paused": "Gepauzeerd na een fout",
        "dash.manual_hold": "Handmatige wijziging op de ketelthermostaat",
        "dash.table.room": "Ruimte",
        "dash.table.now": "Nu",
        "dash.table.aiming": "Doel",
        "dash.table.what": "Wat gebeurt er",
        "dash.options_hint": (
            "Pas schema's, comfort- en lage temperatuur per ruimte aan onder "
            "[Smart Heating-opties]({link}) (Configureren, Ruimte bewerken)."
        ),
        "dash.header_alerts": (
            "{% if n > 0 %}**{{ n }} {{ 'melding heeft' if n == 1 else 'meldingen hebben' }}** aandacht nodig, zie Meldingen hieronder."
            "{% else %}Geen meldingen.{% endif %}"
        ),
        "room_error.invalid_time": "ongeldige tijd {text}",
        "room_error.invalid_days": "ongeldige dagen {text}",
        "room_error.invalid_line": "ongeldige schemaregel {text}",
        "room_error.empty_window": "leeg tijdvak in {text}",
        "room_error.name_required": "naam is verplicht",
        "room_error.name_needs_letters": "de naam heeft minstens één letter of cijfer nodig",
        "room_error.floor_needs_sensor": "een ruimte met vloerverwarming of open radiatoren heeft een temperatuursensor nodig",
        "room_error.trv_required": "radiatorkraan is verplicht (of markeer de ruimte als handmatig)",
        "room_error.comfort_range": "comfort moet {low}-{high} zijn",
        "room_error.frost_min": "vorstbescherming moet minstens {low} zijn",
        "room_error.temp_order": "vorstbescherming <= lage temperatuur <= comfort is vereist",
        "room_error.out_of_range": "{key} moet {low}-{high} zijn",
        "room_error.duplicate_name": "er bestaat al een ruimte met die naam (of een die alleen in hoofdletters of leestekens verschilt)",
        "room_error.duplicate_trv": "die radiatorkraan wordt al door een andere ruimte gebruikt",
        "room_error.unknown_room": "onbekende ruimte {text}",
    },
}
