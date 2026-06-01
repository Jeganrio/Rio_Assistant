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

## Cloud Limitations

The cloud container can serve the web UI, API, weather, news, reminders, briefing,
and other network-based features. Desktop-only features such as local microphone
listening, Windows app control, Spotify desktop automation, screenshots, and
system media keys require your laptop and will not work inside a free cloud
container.

Render free web services can spin down when idle, and free Postgres has platform
limits. Use this deployment for demo/testing, not critical production use.
