# ANIFLIX Poster Maker Bot

A standalone, database-free Telegram bot that creates ANIFLIX anime posters from user-supplied artwork and metadata. It uses the supplied blank design unchanged as `templates/template_01/template.png`, with its editable coordinates described in `config.json`.

## Features

- `/start`, `/create`, `/templates`, `/cancel`, and `/help`.
- Per-user in-memory FSM sessions using aiogram 3.
- Template selection designed for adding more `templates/template_XX/` folders later.
- Proportional artwork fitting with rounded masking and preservation of the supplied decorative circle.
- Wrapped synopsis, fitting title typography, optional IMDb rating and studio fields.
- Temporary image cleanup after success, cancellation, or failures.
- High-quality PNG output.

## Run locally

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Put your Telegram token in .env
python main.py
```

Only `BOT_TOKEN` is required. No MongoDB, PostgreSQL, Redis, SQLite, or other database is used.

## Railway deployment

1. Create a new Railway project from this repository.
2. Railway will use the included `Dockerfile` (or `railway.toml`).
3. Add the environment variable `BOT_TOKEN` in the Railway service Variables panel.
4. Deploy. The process starts with `python main.py` and uses Telegram long polling.

The bot must receive a valid token from BotFather. Do not commit `.env` or the token.

## Adding templates

Create a new folder such as `templates/template_02/` containing `template.png` and `config.json` with the same coordinate keys used by the compositor. The template list is discovered at runtime; no core code change is required.

## Tests

Run:

```bash
pytest -q
```

The tests cover configuration loading, season parsing, title/synopsis handling, optional metadata, artwork fitting, rounded masking, aspect ratios, long input, invalid input, and PNG output.

## Limitations

- Session data is intentionally in memory, so active workflows are lost if the process restarts.
- Telegram long polling is used; run one bot process at a time.
- The current first-party template is the single supplied design. Additional designs must provide their own coordinates in `config.json`.
