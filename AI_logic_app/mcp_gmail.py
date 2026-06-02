from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request # Added: Import Request for token refreshing
import base64
from email.mime.text import MIMEText
import os

from AI_logic_app.google_auth import (
    google_not_connected_message,
    load_authorized_credentials,
    load_client_config,
)

SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.send",
]

class GmailTool:

    name = "gmail"

    description = (
        "Send Gmail emails and check Gmail for interviews, assessments, and meetings."
    )

    def __init__(self, base_dir):
        self.base_dir = base_dir
        self.creds = None # Store credentials here

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

    def _get_authenticated_service(self):
        """
        Authenticates with Gmail API, handling token persistence.
        """
        token_path = os.path.join(self.base_dir, "token.json")
        credentials_path = os.path.join(self.base_dir, "credentials.json")

        self.creds = load_authorized_credentials(
            token_path,
            SCOPES,
            (
                "GOOGLE_GMAIL_TOKEN_JSON",
                "GOOGLE_GMAIL_TOKEN_B64",
                "GOOGLE_TOKEN_JSON",
                "GOOGLE_TOKEN_B64",
            ),
        )

        if self.creds and not self.creds.has_scopes(SCOPES):
            print("Gmail token is missing required scopes. Re-authenticating.")
            self.creds = None

        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request()) # No need for try-except here, let it propagate if it fails
            else:
                is_cloud = os.getenv("CUBY_CLOUD", "").lower() in {"1", "true", "yes"}
                if is_cloud:
                    raise RuntimeError(google_not_connected_message("Gmail"))

                client_config = load_client_config(credentials_path)
                if not client_config:
                    raise RuntimeError(google_not_connected_message("Gmail"))

                flow = InstalledAppFlow.from_client_config(
                    client_config,
                    SCOPES,
                )
                self.creds = flow.run_local_server(port=0)
            
            # Save the credentials for the next run
            with open(token_path, 'w', encoding='utf-8') as token:
                token.write(self.creds.to_json())
        
        return build("gmail", "v1", credentials=self.creds)

    def run(self,
            action="",
            to="",
            subject="",
            body="",
            query="",
            timeframe=""):

        try:
            # Ensure service is authenticated before proceeding
            service = self._get_authenticated_service()

            # SEND MAIL
            if action == "send":
                if not to:
                    return self._err("No recipient email address found.")

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
                    {"to": to, "subject": subject},
                    "Email sent"
                )

            elif action == "check_interviews":
                keywords = [
                    "interview",
                    "assessment",
                    "coding round",
                    "online test",
                    "technical round",
                    "hr round",
                    "aptitude",
                    "assignment",
                    "hacker rank",
                    "hackerrank",
                    "coding challenge",
                    "walk-in",
                    "walkin",
                    "recruiter",
                    "shortlisted",
                    "calendar invite",
                    "scheduled",
                    "meeting",
                    "google meet",
                    "teams meeting",
                    "zoom"
                ]

                gmail_query_parts = []
                
                # Add keywords to the query
                keyword_query = " OR ".join([f'"{k}"' for k in keywords])
                gmail_query_parts.append(f'({keyword_query})')

                # Add timeframe to the query
                if timeframe == "today":
                    gmail_query_parts.append('newer_than:1d')
                elif timeframe == "last week":
                    gmail_query_parts.append('newer_than:7d')
                elif timeframe == "tomorrow":
                    # For "tomorrow", search for the word "tomorrow" in recent emails
                    # This is a heuristic, as Gmail API doesn't have a "received tomorrow" filter.
                    gmail_query_parts.append(f'(tomorrow OR "scheduled for tomorrow")')
                    # Also limit to recent emails to avoid old irrelevant results
                    gmail_query_parts.append('newer_than:7d')
                else:
                    # Default to last 7 days if no specific timeframe is given
                    gmail_query_parts.append('newer_than:7d')

                final_gmail_query = " ".join(gmail_query_parts)
                found = []

                results = service.users().messages().list(
                    userId="me",
                    q=final_gmail_query,
                    maxResults=20 # Increased maxResults for broader search
                ).execute()

                msgs = results.get("messages", [])
                found.extend(msgs)

                detailed_emails = []
                for msg_id in [m['id'] for m in found]:
                    msg_detail = service.users().messages().get(userId='me', id=msg_id, format='metadata', metadataHeaders=['Subject', 'From', 'Date']).execute()
                    subject = next((header['value'] for header in msg_detail['payload']['headers'] if header['name'] == 'Subject'), 'No Subject')
                    sender = next((header['value'] for header in msg_detail['payload']['headers'] if header['name'] == 'From'), 'Unknown Sender')
                    date_received = next((header['value'] for header in msg_detail['payload']['headers'] if header['name'] == 'Date'), 'Unknown Date')
                    detailed_emails.append({
                        'id': msg_id,
                        'subject': subject,
                        'from': sender,
                        'date': date_received,
                        'snippet': msg_detail.get('snippet', '')
                    })

                return self._ok(
                    {"interviews": detailed_emails},
                    f"Found {len(detailed_emails)} interview, assessment, or meeting emails."
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
