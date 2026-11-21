# Tools

Helpers that live next to the integration but are not part of it. Nothing here is installed into Home Assistant.

## Schedule PDF

Makes a printable weekly overview of every room's schedule, with a page per room and a page of talking points.
Handy for agreeing on a schedule with the people you live with.

1. In Home Assistant open **Settings > Devices & services > Smart Heating**, then **Download diagnostics**.
2. Run:

```bash
python -m venv .venv-tools && .venv-tools/bin/pip install -r tools/requirements.txt
.venv-tools/bin/python tools/schedule_pdf.py <diagnostics.json> schedule.pdf --lang en
```

`--lang` is `en` (default) or `nl`. To add a language, add an entry to `TEXTS` in `schedule_pdf.py`.
