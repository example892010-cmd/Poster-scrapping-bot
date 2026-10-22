🎬 ANIFLIX POSTER MAKER BOT

A Telegram bot for creating anime posters using the ANIFLIX template system.

✨ Features

* Generate anime posters using uploaded artwork.
* Add anime title, season, synopsis, genres, and optional rating and studio.
* Preserve the original uploaded character artwork without redrawing it.
* Use replaceable poster templates stored in the repository.
* Keep the existing poster design, layout, colors, and ANIFLIX branding.
* Lightweight HTTP health server for Render Web Service deployment.
* In-memory session handling — no database required.

🛠️ Tech Stack

* Python 3.12
* Aiogram 3
* Pillow
* Asyncio HTTP server

📁 Project Structure

Poster-scrapping-bot/
├── app/
│   ├── handlers/
│   └── services/
│       └── poster_generator.py
├── assets/
│   └── fonts/
├── templates/
│   └── template_01/
├── tests/
│   ├── test_main.py
│   └── test_poster.py
├── main.py
├── Dockerfile
├── requirements.txt
├── .env.example
└── README.md

⚙️ Environment Variables

Required:

* BOT_TOKEN — Telegram bot token from BotFather.

Optional, only if supported by the code:

* OWNER_ID — Telegram owner user ID.
* ADMIN_ID — Telegram admin user ID.

The HTTP server uses Render’s PORT environment variable automatically and falls back to port 10000 for local testing.

Never commit your real bot token to GitHub.

🚀 Deploy on Render

1. Push the latest code to your GitHub repository.
2. Create or open your Render Web Service.
3. Connect the repository: example892010-cmd/Poster-scrapping-bot.
4. Select the main branch.
5. Add BOT_TOKEN under Environment Variables.
6. Deploy the latest commit.
7. Check the deployment logs for both the HTTP server and Telegram bot startup messages.

The bot includes a lightweight HTTP health server so Render can detect an open port. A separate Background Worker is not required for this setup.

❤️ Health Check

After deployment, open your Render service URL:

* / — basic health response.
* /health — health check endpoint.

Expected response:

{"status":"ok"}

Use your actual Render service URL; do not copy an example domain.

🧪 Tests

Run the automated tests with:

pytest -q

Tests help check poster generation and application startup behavior. Passing tests do not guarantee that live Telegram interactions work, so test the bot after deployment.

🤖 Telegram Commands

* /start — start the bot.
* /create — begin poster creation.
* /templates — view available templates.
* /cancel — cancel the current task.
* /help — show help.

Commands depend on the handlers implemented in the repository.

🗄️ Database

No database connection is required. The bot uses repository files for templates and in-memory state for active sessions. Active sessions may reset when the application restarts.

📌 Project

Brand: ANIFLIX NETWORK TAMIL
Handle: @ANIFLIXANIMETAMIL

Made for the ANIFLIX anime community.
