# CUBY Deployment

This project is prepared for local Docker and Render free web-service deployment.

## Local Docker

```powershell
docker compose up --build
```

Open:

```text
http://127.0.0.1:8000/
```

## Render Free Deployment

1. Push this repository to GitHub.
2. In Render, create a new Blueprint from the repository.
3. Render will read `render.yaml`, build `Dockerfile`, and create:
   - `cuby-assistant` web service
   - `cuby-db` free Postgres database
4. Set private API keys in the Render dashboard, not in Git:
   - `OPENAI_API_KEY`
   - `GNEWS_API_KEY`
   - `AVIATIONSTACK_KEY`
   - `GOOGLE_CREDENTIALS_B64`
   - `GOOGLE_TOKEN_B64` or separate `GOOGLE_GMAIL_TOKEN_B64` and `GOOGLE_CALENDAR_TOKEN_B64`

To enable Gmail and Calendar on Render, run this locally after Google sign-in
has created `credentials.json`, `token.json`, and `calendar_token.json`:

```powershell
python scripts/export_google_env.py
```

Copy the printed values into Render's Environment tab as secret variables.
Never paste those values into GitHub or documentation.

## Cloud Limitations

The cloud container can serve the web UI, API, weather, news, reminders, briefing,
and other network-based features. On Render, CUBY uses the browser microphone
and browser speech synthesis from the web page. Desktop-only features such as
Windows app control, Spotify desktop automation, screenshots, and system media
keys require your laptop and will not work inside a free cloud container.

Render free web services can spin down when idle, and free Postgres has platform
limits. Use this deployment for demo/testing, not critical production use.
