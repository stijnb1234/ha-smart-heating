# Contributing

Thanks for helping. Bug reports, ideas and pull requests are all welcome.

## Reporting a problem

Open an [issue](https://github.com/stijnb1234/ha-smart-heating/issues/new/choose) and fill in the form. Diagnostics (Settings → Devices & services → Smart Heating → ⋮ → Download diagnostics) and the relevant log lines make it much easier to find the cause.

## Setting up

```bash
python3.13 -m venv .venv && .venv/bin/pip install -r requirements-test.txt
.venv/bin/ruff check .
.venv/bin/mypy
.venv/bin/pytest -q
```

## How the code is organised

- Decision logic lives in `custom_components/smart_heating/engine/`, a pure Python engine with no Home Assistant imports, tested with a fake clock in `tests/engine/`. Put new logic there when you can.
- Glue around it (reading states, writing commands, config flow, dashboard) is in `custom_components/smart_heating/`.
- Vocabulary is in [GLOSSARY.md](GLOSSARY.md), decisions in [docs/adr/](docs/adr/), the overall shape in [docs/design.md](docs/design.md).

## Pull requests

- Keep a change focused, and add a test for new behaviour.
- Keep docs and UI texts generic: no names, brands or entity ids of your own home.
- Update the README or the manuals in `docs/` when what users see changes. UI texts exist in English and Dutch (`translations/`, `i18n.py`).
- CI must pass: ruff, mypy, pytest, hassfest and the HACS validation.

## Releases

Maintainers release by bumping `version` in `manifest.json` and pushing a tag `v<version>`.
