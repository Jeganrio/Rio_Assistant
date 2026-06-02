from apscheduler.schedulers.background import BackgroundScheduler
from cuby.mcp_tools import mcp
from cuby.config import settings
import datetime
import json

scheduler = BackgroundScheduler()
_LAST_WEATHER_ALERT_KEY = ""
_LAST_UTILITY_ALERT_KEY = ""
_NOTIFIED_CALENDAR_EVENTS = set()
_WEATHER_STATE_PATH = settings.DATA_DIR / "weather_alert_state.json"
_UTILITY_STATE_PATH = settings.DATA_DIR / "utility_alert_state.json"


def _load_weather_alert_key() -> str:
    try:
        if _WEATHER_STATE_PATH.exists():
            data = json.loads(_WEATHER_STATE_PATH.read_text(encoding="utf-8"))
            return str(data.get("last_alert_key", ""))
    except Exception:
        pass
    return ""


def _save_weather_alert_key(value: str) -> None:
    try:
        _WEATHER_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        _WEATHER_STATE_PATH.write_text(
            json.dumps({"last_alert_key": value}, indent=2),
            encoding="utf-8",
        )
    except Exception:
        pass


def _load_utility_alert_key() -> str:
    try:
        if _UTILITY_STATE_PATH.exists():
            data = json.loads(_UTILITY_STATE_PATH.read_text(encoding="utf-8"))
            return str(data.get("last_alert_key", ""))
    except Exception:
        pass
    return ""


def _save_utility_alert_key(value: str) -> None:
    try:
        _UTILITY_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        _UTILITY_STATE_PATH.write_text(
            json.dumps({"last_alert_key": value}, indent=2),
            encoding="utf-8",
        )
    except Exception:
        pass

def check_interviews():

    result = mcp.run(
        "gmail",
        action="check_interviews"
    )

    if result["status"] == "ok":

        interviews = result["data"].get(
            "interviews",
            []
        )

        if interviews:

            mcp.run(
                "notification",
                title="CUBY Mail Alert",
                message=f"{len(interviews)} interview, assessment, or meeting emails found"
            )

def check_weather_alert():
    global _LAST_WEATHER_ALERT_KEY

    result = mcp.run(
        "weather",
        city=settings.WEATHER_ALERT_CITY,
        rain_alert_hours=max(settings.WEATHER_ALERT_HOURS, 24)
    )

    if result["status"] != "ok":
        return

    data = result.get("data") or {}
    upcoming_rain = data.get("upcoming_rain", [])
    suggested_reminder = data.get("suggested_reminder") or {}

    if not upcoming_rain and not data.get("heat_alert"):
        return

    alert_key = (
        suggested_reminder.get("weather_time")
        or (upcoming_rain[0].get("time", "") if upcoming_rain else "")
        or data.get("heat_summary", "")
    )
    persisted_key = _load_weather_alert_key()
    if alert_key and (alert_key == _LAST_WEATHER_ALERT_KEY or alert_key == persisted_key):
        return
    _LAST_WEATHER_ALERT_KEY = alert_key
    if alert_key:
        _save_weather_alert_key(alert_key)

    message = " ".join((data.get("smart_advice") or [])[:2]) or data.get("summary", "")
    mcp.run(
        "notification",
        title="CUBY Weather Alert",
        message=message[:250]
    )

    if (
        upcoming_rain
        and getattr(settings, "WEATHER_AUTO_REMINDER_ENABLED", True)
        and suggested_reminder.get("text")
        and suggested_reminder.get("due_at")
    ):
        mcp.run(
            "reminders",
            action="add",
            text=suggested_reminder["text"],
            due_at=suggested_reminder["due_at"],
            source="weather",
        )


def check_utility_alerts():
    global _LAST_UTILITY_ALERT_KEY

    if not getattr(settings, "UTILITY_ALERT_ENABLED", True):
        return

    result = mcp.run(
        "utility_alerts",
        kind="all",
        location=getattr(settings, "UTILITY_ALERT_LOCATION", "Ponnagar, Karumandapam, Trichy"),
        city=settings.WEATHER_ALERT_CITY or "Trichy",
        days=3,
        max_results=5,
    )

    if result["status"] != "ok":
        return

    alerts = (result.get("data") or {}).get("alerts", [])
    if not alerts:
        return

    alert_key = "|".join(
        f"{alert.get('type')}:{alert.get('title') or alert.get('url') or alert.get('snippet', '')[:80]}"
        for alert in alerts[:3]
    )
    persisted_key = _load_utility_alert_key()
    if alert_key and (alert_key == _LAST_UTILITY_ALERT_KEY or alert_key == persisted_key):
        return

    _LAST_UTILITY_ALERT_KEY = alert_key
    if alert_key:
        _save_utility_alert_key(alert_key)

    top = alerts[0]
    label = "Power" if top.get("type") == "power" else "Water"
    message = (
        f"{label} alert for {getattr(settings, 'UTILITY_ALERT_LOCATION', 'your area')}: "
        f"{top.get('title') or top.get('snippet', 'check official source')}"
    )
    mcp.run(
        "notification",
        title="CUBY Utility Alert",
        message=message[:250],
    )


def check_calendar_alerts():
    if not settings.CALENDAR_ALERT_ENABLED:
        return

    result = mcp.run(
        "calendar",
        action="upcoming",
        timeframe="upcoming",
        max_results=5,
        window_minutes=settings.CALENDAR_ALERT_LOOKAHEAD_MINUTES,
        interactive=False,
    )

    if result["status"] != "ok":
        return

    events = (result.get("data") or {}).get("calendar_events", [])
    for event in events:
        if event.get("all_day"):
            continue

        event_id = event.get("id") or f"{event.get('summary')}:{event.get('start')}"
        if not event_id or event_id in _NOTIFIED_CALENDAR_EVENTS:
            continue

        _NOTIFIED_CALENDAR_EVENTS.add(event_id)
        minutes = event.get("starts_in_minutes")
        when = event.get("start_text", "soon")
        if minutes is not None and minutes >= 0:
            when = f"in {minutes} minute(s)"

        mcp.run(
            "notification",
            title="CUBY Meeting Alert",
            message=f"{event.get('summary', 'Calendar event')} starts {when}."
        )


def check_due_reminders():
    result = mcp.run(
        "reminders",
        action="due",
        mark_notified=True,
    )

    if result["status"] != "ok":
        return

    reminders = (result.get("data") or {}).get("reminders", [])
    for reminder in reminders:
        mcp.run(
            "notification",
            title="CUBY Reminder",
            message=reminder.get("text", "Reminder due")
        )


scheduler.add_job(
    check_interviews,
    "interval",
    minutes=30
)

scheduler.add_job(
    check_weather_alert,
    "interval",
    minutes=settings.WEATHER_ALERT_INTERVAL_MINUTES,
    next_run_time=datetime.datetime.now(),
)

scheduler.add_job(
    check_utility_alerts,
    "interval",
    minutes=getattr(settings, "UTILITY_ALERT_INTERVAL_MINUTES", 60),
)

scheduler.add_job(
    check_calendar_alerts,
    "interval",
    minutes=5
)

scheduler.add_job(
    check_due_reminders,
    "interval",
    minutes=1
)

