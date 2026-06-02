from __future__ import annotations

import datetime
import json
import re
import threading
import uuid
from pathlib import Path
from typing import Any


class ReminderTool:
    name = "reminders"
    description = "Create, list, complete, delete, and notify local reminders."

    def __init__(self, base_dir):
        self.base_dir = Path(base_dir)
        self.path = self.base_dir / "AI_logic_app" / "data" / "reminders.json"
        self._lock = threading.Lock()

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

    @staticmethod
    def _now() -> datetime.datetime:
        return datetime.datetime.now().astimezone()

    @staticmethod
    def _parse_dt(value: str) -> datetime.datetime | None:
        if not value:
            return None
        try:
            parsed = datetime.datetime.fromisoformat(value)
            if parsed.tzinfo is None:
                parsed = parsed.astimezone()
            return parsed
        except Exception:
            return None

    @staticmethod
    def _format_dt(value: str) -> str:
        parsed = ReminderTool._parse_dt(value)
        if not parsed:
            return ""
        return parsed.astimezone().strftime("%d %b %Y, %I:%M %p")

    def _load(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return data
        except Exception:
            pass
        return []

    def _save(self, reminders: list[dict[str, Any]]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(reminders, indent=2), encoding="utf-8")

    def _active_sorted(self, reminders: list[dict[str, Any]]) -> list[dict[str, Any]]:
        active = [
            r for r in reminders
            if not r.get("completed") and not self._is_weather_generated(r)
        ]
        return sorted(active, key=lambda r: (r.get("due_at") or "9999", r.get("created_at", "")))

    @staticmethod
    def _normalize_key(value: str) -> str:
        return " ".join(re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).split())

    def _is_expired(self, reminder: dict[str, Any], now: datetime.datetime) -> bool:
        due = self._parse_dt(reminder.get("due_at", ""))
        return bool(due and due.astimezone() < now)

    @staticmethod
    def _is_weather_generated(reminder: dict[str, Any]) -> bool:
        text = ReminderTool._normalize_key(reminder.get("text", ""))
        source = ReminderTool._normalize_key(reminder.get("source", ""))
        weather_terms = (
            "rain possible",
            "heavy rain",
            "moderate rain",
            "light rain",
            "carry umbrella",
            "umbrella",
            "raincoat",
            "weather alert",
            "heat alert",
            "stay hydrated",
        )
        return source == "weather" or any(term in text for term in weather_terms)

    def _visible_sorted(
        self,
        reminders: list[dict[str, Any]],
        include_completed: bool,
        now: datetime.datetime,
    ) -> list[dict[str, Any]]:
        if include_completed:
            items = reminders
        else:
            items = [
                r for r in reminders
                if (
                    not r.get("completed")
                    and not self._is_expired(r, now)
                    and not self._is_weather_generated(r)
                )
            ]
        return sorted(
            items,
            key=lambda r: (
                bool(r.get("completed")),
                r.get("due_at") or "9999",
                r.get("created_at", ""),
            ),
        )

    def _find_reminder(
        self,
        reminders: list[dict[str, Any]],
        reminder_id: str,
        now: datetime.datetime,
        text: str = "",
    ) -> dict[str, Any] | None:
        key = self._normalize_key(reminder_id or text)
        if not key:
            return None

        active = self._visible_sorted(reminders, include_completed=False, now=now)
        if key.isdigit():
            index = int(key) - 1
            if 0 <= index < len(active):
                return active[index]

        for reminder in reminders:
            rid = str(reminder.get("id", "")).lower()
            if rid == key or rid.startswith(key):
                return reminder
            reminder_text = self._normalize_key(reminder.get("text", ""))
            if reminder_text and (key == reminder_text or key in reminder_text or reminder_text in key):
                return reminder
        return None

    def _serialize(
        self,
        reminders: list[dict[str, Any]],
        include_completed: bool,
        now: datetime.datetime | None = None,
    ) -> list[dict[str, Any]]:
        now = now or self._now()
        items = self._visible_sorted(reminders, include_completed, now)
        serialized = []
        for index, reminder in enumerate(items, 1):
            item = dict(reminder)
            item["number"] = index
            item["due_text"] = self._format_dt(reminder.get("due_at", ""))
            item["expired"] = self._is_expired(reminder, now)
            serialized.append(item)
        return serialized

    def run(
        self,
        action: str = "list",
        text: str = "",
        due_at: str = "",
        reminder_id: str = "",
        include_completed: bool = False,
        window_minutes: int = 0,
        max_results: int = 20,
        mark_notified: bool = False,
        source: str = "",
    ) -> dict:
        action = (action or "list").lower().strip()

        with self._lock:
            reminders = self._load()
            now = self._now()

            if action == "add":
                text = (text or "").strip()
                if not text:
                    return self._err("Reminder text is required.")
                parsed_due = self._parse_dt(due_at)
                normalized_text = self._normalize_key(text)
                normalized_due = parsed_due.isoformat() if parsed_due else ""
                for existing in reminders:
                    if existing.get("completed"):
                        continue
                    existing_due = self._parse_dt(existing.get("due_at", ""))
                    existing_due_text = existing_due.isoformat() if existing_due else ""
                    if (
                        self._normalize_key(existing.get("text", "")) == normalized_text
                        and existing_due_text == normalized_due
                    ):
                        due_text = self._format_dt(existing.get("due_at", ""))
                        message = f"Reminder already exists: {existing.get('text', text)}"
                        if due_text:
                            message += f" at {due_text}"
                        return self._ok({"reminder": existing, "duplicate": True}, message)
                reminder = {
                    "id": uuid.uuid4().hex[:8],
                    "text": text,
                    "due_at": parsed_due.isoformat() if parsed_due else "",
                    "created_at": now.isoformat(),
                    "completed": False,
                    "completed_at": "",
                    "notified": False,
                    "notified_at": "",
                    "source": (source or "").strip(),
                }
                reminders.append(reminder)
                self._save(reminders)
                due_text = self._format_dt(reminder["due_at"])
                message = f"Reminder saved: {text}"
                if due_text:
                    message += f" at {due_text}"
                return self._ok({"reminder": reminder}, message)

            if action in {"list", "show"}:
                items = self._serialize(reminders, include_completed, now)[:max(1, int(max_results or 20))]
                active_count = len([
                    r for r in reminders
                    if (
                        not r.get("completed")
                        and not self._is_expired(r, now)
                        and not self._is_weather_generated(r)
                    )
                ])
                expired_count = len([
                    r for r in reminders
                    if not r.get("completed") and self._is_expired(r, now)
                ])
                return self._ok(
                    {
                        "reminders": items,
                        "count": len(items),
                        "active_count": active_count,
                        "expired_count": expired_count,
                    },
                    f"Found {active_count} active reminder(s).",
                )

            if action in {"due", "notify_due"}:
                window = max(0, int(window_minutes or 0))
                due_items = []
                for reminder in self._active_sorted(reminders):
                    due = self._parse_dt(reminder.get("due_at", ""))
                    if not due or reminder.get("notified"):
                        continue
                    limit = now + datetime.timedelta(minutes=window)
                    if due <= limit:
                        if mark_notified or action == "notify_due":
                            reminder["notified"] = True
                            reminder["notified_at"] = now.isoformat()
                        due_items.append(reminder)
                if mark_notified or action == "notify_due":
                    self._save(reminders)
                return self._ok(
                    {"reminders": self._serialize(due_items, include_completed=True, now=now), "count": len(due_items)},
                    f"Found {len(due_items)} due reminder(s).",
                )

            if action in {"complete", "done"}:
                reminder = self._find_reminder(reminders, reminder_id, now, text=text)
                if not reminder:
                    return self._err("Reminder not found.")
                reminder["completed"] = True
                reminder["completed_at"] = now.isoformat()
                self._save(reminders)
                return self._ok({"reminder": reminder}, f"Completed reminder: {reminder.get('text', '')}")

            if action in {"delete", "remove", "cancel"}:
                target = self._normalize_key(reminder_id or text)
                if target in {"all", "all reminder", "all reminders", "everything", "every reminder", "every reminders"}:
                    deleted = [r for r in reminders if not r.get("completed")]
                    reminders = [r for r in reminders if r.get("completed")]
                    self._save(reminders)
                    return self._ok(
                        {"deleted_count": len(deleted), "reminders": deleted},
                        f"Deleted {len(deleted)} reminder(s).",
                    )

                reminder = self._find_reminder(reminders, reminder_id, now, text=text)
                if not reminder:
                    return self._err("Reminder not found.")
                reminders = [r for r in reminders if r.get("id") != reminder.get("id")]
                self._save(reminders)
                return self._ok({"reminder": reminder}, f"Deleted reminder: {reminder.get('text', '')}")

            return self._err(f"Unknown reminder action: {action}")
