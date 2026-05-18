from selenium import webdriver
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import time

class JobTool:

    name = "jobs"

    description = (
        "Search jobs on LinkedIn, Naukri and Indeed."
    )

    def _ok(self, data=None, message="Success"):
        return {
            "status": "ok",
            "data": data or {},
            "message": message
        }

    def _err(self, message):
        return {
            "status": "error",
            "data": None,
            "message": message
        }

    def run(self,
            platform="linkedin",
            role="python developer",
            location="remote"):

        try:

            from selenium.webdriver.chrome.service import Service
            from webdriver_manager.chrome import ChromeDriverManager

            service = Service(
                ChromeDriverManager().install()
            )

            driver = webdriver.Chrome(service=service)

            if platform == "linkedin":

                url = (
                    "https://www.linkedin.com/jobs/search/"
                    f"?keywords={role}"
                    f"&location={location}"
                )

            elif platform == "naukri":

                url = (
                    f"https://www.naukri.com/{role}-jobs"
                )

            else:

                url = (
                    f"https://in.indeed.com/jobs?q={role}"
                )

            driver.get(url)

            return self._ok(
                {"url": url},
                f"Opened {platform} jobs"
            )

        except Exception as e:
            return self._err(str(e))