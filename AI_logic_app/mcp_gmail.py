from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import base64
from email.mime.text import MIMEText

SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify"
]

class GmailTool:

    name = "gmail"

    description = (
        "Read, send and search Gmail emails."
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

    def _service(self):

        flow = InstalledAppFlow.from_client_secrets_file(
            "credentials.json",
            SCOPES
        )

        creds = flow.run_local_server(port=0)

        return build("gmail", "v1", credentials=creds)

    def run(self,
            action="",
            to="",
            subject="",
            body="",
            query=""):

        try:

            service = self._service()

            # SEND MAIL
            if action == "send":

                message = MIMEText(body)

                message["to"] = to
                message["subject"] = subject

                raw = base64.urlsafe_b64encode(
                    message.as_bytes()
                ).decode()

                service.users().messages().send(
                    userId="me",
                    body={"raw": raw}
                ).execute()

                return self._ok(
                    message="Email sent"
                )
            elif action == "check_interviews":

                keywords = [
                    "interview",
                    "assessment",
                    "coding round",
                    "online test",
                    "technical round",
                    "hr round"
                ]

                found = []

                for keyword in keywords:

                    results = service.users().messages().list(
                        userId="me",
                        q=f"{keyword} newer_than:1d",
                        maxResults=10
                    ).execute()

                    msgs = results.get("messages", [])

                    if msgs:
                        found.extend(msgs)

                return self._ok(
                    {"interviews": found},
                    f"Found {len(found)} interview related emails"
                )

            # SEARCH MAIL
            elif action == "search":

                results = service.users().messages().list(
                    userId="me",
                    q=query,
                    maxResults=10
                ).execute()

                messages = results.get("messages", [])

                return self._ok(
                    {"emails": messages},
                    f"Found {len(messages)} emails"
                )

            return self._err("Unknown action")

            

        except Exception as e:
            return self._err(str(e))