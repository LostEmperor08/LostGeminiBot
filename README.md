# LostGeminiBot

LostGeminiBot is a Python Telegram study bot that combines:

- AI Q&A replies with provider fallback (**OpenAI → Gemini**)
- A daily credit system (regular users, VIP users, and quiz bonus credits)
- Hourly Telegram quiz polls with bonus rewards
- A simple leaderboard and owner-only admin commands

## Features

- **Telegram bot commands** for onboarding and utilities (`/start`, `/help`, `/ping`)
- **AI answers** via `/ai <question>`
  - Uses `gpt-4o-mini` first
  - Falls back to `gemini-1.5-flash` if OpenAI fails
- **Daily credits + cooldown**
  - Normal users: 2 credits/day
  - VIP users: 25 credits/day
  - 5-second per-user cooldown on `/ai`
- **Quiz system**
  - Hourly quiz poll rotation across Physics/Chemistry/Mathematics/Biology
  - Correct answers grant bonus credits and increase leaderboard score
- **Owner commands**
  - `/addvip <user_id>`
  - `/removevip <user_id>`
  - `/status`

## Tech Stack

- Python 3.11
- `python-telegram-bot` (async command + polling bot)
- `openai`
- `google-genai`
- JSON file storage (no database)

## Project Structure

```text
.
├── bot.py            # Main bot logic and command handlers
├── requirements.txt  # Python dependencies
├── runtime.txt       # Runtime pin (python-3.11.9)
└── README.md
```

## Prerequisites

- Python 3.11+
- A Telegram bot token from [@BotFather](https://t.me/BotFather)
- OpenAI API key
- Google Gemini API key

## Setup

1. Clone the repository and move into it.
2. Create and activate a virtual environment.
3. Install dependencies.
4. Set required environment variables.
5. Run the bot.

Example (Linux/macOS):

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export BOT_TOKEN="your_telegram_bot_token"
export OPENAI_API_KEY="your_openai_key"
export GEMINI_API_KEY="your_gemini_key"
python bot.py
```

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `BOT_TOKEN` | Yes | Telegram bot token used by `python-telegram-bot`. |
| `OPENAI_API_KEY` | Yes | OpenAI key for the primary AI response provider. |
| `GEMINI_API_KEY` | Yes | Gemini key used as fallback AI provider. |

> Never commit real tokens or API keys. Use environment variables only.

## Commands

### User commands

- `/start` - Bot intro
- `/help` - Command list
- `/ai <question>` - Ask AI and consume credits
- `/leaderboard` - Top quiz scores
- `/onquiz` - Start hourly quiz
- `/offquiz` - Stop quiz
- `/ping` - Bot uptime

### Owner-only commands

- `/addvip <user_id>`
- `/removevip <user_id>`
- `/status`

## Data Storage

The bot writes JSON files under:

- `/opt/render/project/src/data/users.json`
- `/opt/render/project/src/data/vip.json`
- `/opt/render/project/src/data/leaderboard.json`

This path is created automatically at runtime.

## Deployment Notes

This repository includes `runtime.txt` (`python-3.11.9`) and uses a Render-style data path (`/opt/render/project/src/data`), so it can be deployed on platforms that support Python runtime files and long-running worker processes.

Typical start command:

```bash
python bot.py
```

## Current Limitations

- `OWNER_ID` and `OWNER_USERNAME` are hardcoded in `bot.py`.
- Quiz questions are currently static placeholders (`What is 5 × 3?`).
- Leaderboard displays user IDs, not Telegram usernames.

## License

No license file is currently included in this repository.
