from __future__ import annotations

import time
import re
import webbrowser
from urllib.parse import quote_plus


class JobTool:
    name = "jobs"
    description = "Search jobs and open guided apply pages on LinkedIn, Naukri, and Indeed."

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
    def _slug(value: str) -> str:
        value = (value or "").strip().lower()
        value = re.sub(r"[^a-z0-9]+", "-", value)
        return value.strip("-") or "jobs"

    @staticmethod
    def _clean(value: str, fallback: str) -> str:
        value = re.sub(r"\s+", " ", str(value or "")).strip(" .,-")
        return value or fallback

    @staticmethod
    def _clean_roles(roles, role: str) -> list[str]:
        if isinstance(roles, str):
            raw_roles = re.split(r"\s*(?:,|/|\bor\b|\band\b)\s*", roles)
        elif isinstance(roles, (list, tuple, set)):
            raw_roles = list(roles)
        else:
            raw_roles = [role]

        cleaned = []
        for item in raw_roles:
            value = re.sub(r"\s+", " ", str(item or "")).strip(" .,-")
            if value and value.lower() not in {entry.lower() for entry in cleaned}:
                cleaned.append(value)
        return cleaned or [JobTool._clean(role, "python developer")]

    def _build_url(self, platform: str, role: str, location: str) -> str:
        role_q = quote_plus(role)
        location_q = quote_plus(location)
        role_slug = self._slug(role)
        location_slug = self._slug(location)

        if platform == "linkedin":
            return (
                "https://www.linkedin.com/jobs/search/"
                f"?keywords={role_q}&location={location_q}"
            )

        if platform == "naukri":
            if location and location.lower() not in {"remote", "anywhere", "india"}:
                return f"https://www.naukri.com/{role_slug}-jobs-in-{location_slug}"
            return f"https://www.naukri.com/{role_slug}-jobs"

        return f"https://in.indeed.com/jobs?q={role_q}&l={location_q}"

    def run(
        self,
        platform="linkedin",
        role="python developer",
        location="remote",
        action="search",
        auto_apply=False,
        max_jobs=5,
        roles=None,
    ):
        try:
            platform = self._clean(platform, "linkedin").lower()
            if platform not in {"linkedin", "naukri", "indeed"}:
                platform = "linkedin"

            role = self._clean(role, "python developer")
            role_list = self._clean_roles(roles, role)
            location = self._clean(location, "remote")
            action = self._clean(action, "search").lower()
            max_jobs = max(1, min(int(max_jobs or 5), 20))
            wants_apply = auto_apply or action in {"apply", "auto_apply", "guided_apply"}

            urls = []
            opened_count = 0
            for item in role_list:
                url = self._build_url(platform, item, location)
                urls.append({"role": item, "url": url})
                if webbrowser.open(url):
                    opened_count += 1
                time.sleep(0.25)

            data = {
                "platform": platform,
                "role": role_list[0],
                "roles": role_list,
                "location": location,
                "url": urls[0]["url"],
                "urls": urls,
                "opened": opened_count > 0,
                "opened_count": opened_count,
                "action": "guided_apply" if wants_apply else "search",
                "max_jobs": max_jobs,
                "submitted": False,
            }

            if platform == "naukri" and wants_apply:
                data["requires_user_review"] = True
                role_text = ", ".join(role_list)
                return self._ok(
                    data,
                    (
                        f"Opened Naukri apply queue for {role_text} in {location}. "
                        f"I opened {opened_count} search tab(s). "
                        "I will not press the final Apply/Submit button automatically because that sends your profile to companies."
                    ),
                )

            if wants_apply:
                data["requires_user_review"] = True
                role_text = ", ".join(role_list)
                return self._ok(
                    data,
                    (
                        f"Opened {platform} jobs for {role_text} in {location}. "
                        "Review the job details before applying."
                    ),
                )

            role_text = ", ".join(role_list)
            return self._ok(
                data,
                f"Opened {platform} jobs for {role_text} in {location}.",
            )

        except Exception as e:
            return self._err(str(e))
