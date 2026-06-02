from __future__ import annotations

import datetime
import os
import webbrowser
from typing import Any

from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from AI_logic_app.google_auth import (
    google_not_connected_message,
    load_authorized_credentials,
    load_client_config,
)


SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]


class CalendarTool:
    name = "calendar"
    description = "Check Google Calendar for meetings, appointments, and upcoming events."

    def __init__(self, base_dir):
        self.base_dir = str(base_dir)
        self.creds = None

    def _ok(self, data=None, message="Success"):
        return {
            "status": "ok",
            "data": data or {},
            "message": message,
        }

    def _err(self, message):
        return {
            "status": "error",
            "data": None,
            "message": message,
        }

    def _get_authenticated_service(self, interactive: bool = True):
        token_path = os.path.join(self.base_dir, "calendar_token.json")
        credentials_path = os.path.join(self.base_dir, "credentials.json")

        self.creds = load_authorized_credentials(
            token_path,
            SCOPES,
            (
                "GOOGLE_CALENDAR_TOKEN_JSON",
                "GOOGLE_CALENDAR_TOKEN_B64",
                "GOOGLE_TOKEN_JSON",
                "GOOGLE_TOKEN_B64",
            ),
        )

        if self.creds and not self.creds.has_scopes(SCOPES):
            print("Calendar token is missing required scopes. Re-authenticating.")
            self.creds = None

        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                try:
                    self.creds.refresh(Request())
                except Exception:
                    self.creds = None

            if not self.creds or not self.creds.valid:
                is_cloud = os.getenv("CUBY_CLOUD", "").lower() in {"1", "true", "yes"}
                if not interactive or is_cloud:
                    raise RuntimeError(google_not_connected_message("Google Calendar"))

                client_config = load_client_config(credentials_path)
                if not client_config:
                    raise RuntimeError(google_not_connected_message("Google Calendar"))

                flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
                self.creds = flow.run_local_server(port=0)

            with open(token_path, "w", encoding="utf-8") as token:
                token.write(self.creds.to_json())

        return build("calendar", "v3", credentials=self.creds)

    def _calendar_api_enable_url(self) -> str:
        credentials_path = os.path.join(self.base_dir, "credentials.json")
        fallback = "https://console.cloud.google.com/apis/library/calendar-json.googleapis.com"

        try:
            raw = load_client_config(credentials_path) or {}
            client = raw.get("installed") or raw.get("web") or {}
            project = client.get("project_id", "")
            if not project:
                client_id = client.get("client_id", "")
                project = client_id.split("-", 1)[0] if "-" in client_id else ""
            if project:
                return (
                    "https://console.developers.google.com/apis/api/"
                    f"calendar-json.googleapis.com/overview?project={project}"
                )
        except Exception:
            pass

        return fallback

    def _calendar_api_disabled_error(self, interactive: bool) -> dict:
        enable_url = self._calendar_api_enable_url()
        opened = False
        if interactive:
            try:
                webbrowser.open(enable_url)
                opened = True
            except Exception:
                opened = False

        message = (
            "Google Calendar API is disabled for this Google Cloud project. "
            "Enable Google Calendar API in Google Cloud Console, wait a few minutes, "
            "then ask me to check your calendar again."
        )
        if opened:
            message = (
                "Google Calendar API is disabled for this Google Cloud project. "
                "I opened the enable page. Enable it, wait a few minutes, then ask me again."
            )

        return {
            "status": "error",
            "data": {
                "reason": "calendar_api_disabled",
                "enable_url": enable_url,
                "opened_enable_page": opened,
            },
            "message": message,
        }

    @staticmethod
    def _local_now() -> datetime.datetime:
        return datetime.datetime.now().astimezone()

    def _time_range(
        self,
        timeframe: str = "",
        window_minutes: int = 0,
        target_date: str = "",
    ) -> tuple[datetime.datetime, datetime.datetime, str]:
        now = self._local_now()
        key = (timeframe or "").lower().strip()

        if target_date:
            try:
                date_value = datetime.date.fromisoformat(target_date)
                start = datetime.datetime.combine(
                    date_value,
                    datetime.time.min,
                    tzinfo=now.tzinfo,
                )
                return start, start + datetime.timedelta(days=1), date_value.strftime("%A")
            except Exception:
                pass

        if window_minutes and window_minutes > 0:
            return now, now + datetime.timedelta(minutes=window_minutes), "upcoming"

        if key in {"tomorrow", "next day"}:
            start = (now + datetime.timedelta(days=1)).replace(
                hour=0,
                minute=0,
                second=0,
                microsecond=0,
            )
            return start, start + datetime.timedelta(days=1), "tomorrow"

        if key in {"week", "this week", "next 7 days", "7 days"}:
            return now, now + datetime.timedelta(days=7), "this week"

        if key in {"upcoming", "next", "later"}:
            return now, now + datetime.timedelta(days=1), "upcoming"

        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        return start, start + datetime.timedelta(days=1), "today"

    @staticmethod
    def _parse_calendar_datetime(value: str) -> datetime.datetime | None:
        if not value or "T" not in value:
            return None
        try:
            return datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
        except Exception:
            return None

    def _format_event(
        self,
        event: dict[str, Any],
        now: datetime.datetime,
    ) -> dict[str, Any]:
        start_value = event.get("start", {}).get("dateTime") or event.get("start", {}).get("date", "")
        end_value = event.get("end", {}).get("dateTime") or event.get("end", {}).get("date", "")
        start_dt = self._parse_calendar_datetime(start_value)
        end_dt = self._parse_calendar_datetime(end_value)
        all_day = start_dt is None

        if start_dt:
            start_text = start_dt.astimezone().strftime("%d %b %Y, %I:%M %p")
            starts_in_minutes = int((start_dt.astimezone() - now).total_seconds() / 60)
        else:
            start_text = f"{start_value} all day" if start_value else "No start time"
            starts_in_minutes = None

        if end_dt:
            end_text = end_dt.astimezone().strftime("%d %b %Y, %I:%M %p")
        else:
            end_text = f"{end_value} all day" if end_value else ""

        meet_link = event.get("hangoutLink", "")
        for entry in event.get("conferenceData", {}).get("entryPoints", []) or []:
            if entry.get("entryPointType") == "video" and entry.get("uri"):
                meet_link = entry["uri"]
                break

        attendees = event.get("attendees") or []
        return {
            "id": event.get("id", ""),
            "summary": event.get("summary", "No title"),
            "start": start_value,
            "end": end_value,
            "start_text": start_text,
            "end_text": end_text,
            "starts_in_minutes": starts_in_minutes,
            "all_day": all_day,
            "location": event.get("location", ""),
            "meet_link": meet_link,
            "html_link": event.get("htmlLink", ""),
            "organizer": (event.get("organizer") or {}).get("email", ""),
            "attendee_count": len(attendees),
        }

    def run(
        self,
        action: str = "upcoming",
        timeframe: str = "today",
        max_results: int = 10,
        window_minutes: int = 0,
        target_date: str = "",
        interactive: bool = True,
    ):
        try:
            service = self._get_authenticated_service(interactive=interactive)

            if action not in {"upcoming", "list", "check_meetings"}:
                action = "upcoming"

            start, end, label = self._time_range(
                timeframe,
                window_minutes,
                target_date=target_date,
            )
            max_results = max(1, min(int(max_results or 10), 20))

            events_result = service.events().list(
                calendarId="primary",
                timeMin=start.isoformat(),
                timeMax=end.isoformat(),
                maxResults=max_results,
                singleEvents=True,
                orderBy="startTime",
            ).execute()

            now = self._local_now()
            events = [
                self._format_event(event, now)
                for event in events_result.get("items", [])
            ]

            return self._ok(
                {
                    "calendar_events": events,
                    "timeframe": label,
                    "start": start.isoformat(),
                    "end": end.isoformat(),
                    "count": len(events),
                },
                f"Found {len(events)} calendar event(s) for {label}.",
            )

        except HttpError as exc:
            error_text = str(exc).lower()
            if (
                getattr(exc, "status_code", None) == 403
                or getattr(getattr(exc, "resp", None), "status", None) == 403
            ) and (
                "accessnotconfigured" in error_text
                or "calendar api has not been used" in error_text
                or "disabled" in error_text
            ):
                return self._calendar_api_disabled_error(interactive)
            return self._err(f"Google Calendar request failed: {exc.reason}")

        except Exception as exc:
            return self._err(str(exc))
