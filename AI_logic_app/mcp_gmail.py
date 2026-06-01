from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request # Added: Import Request for token refreshing
from googleapiclient.errors import HttpError # Import HttpError
import base64
import json
from email.mime.text import MIMEText
import os
import datetime # Import datetime for date calculations
from datetime import timedelta # Import timedelta
import pickle

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

        if os.path.exists(token_path):
            try:
                with open(token_path, 'rb') as token:
                    token_data = token.read()
                try:
                    self.creds = pickle.loads(token_data)
                except Exception:
                    self.creds = Credentials.from_authorized_user_info(
                        json.loads(token_data.decode("utf-8")),
                        SCOPES
                    )
            except Exception as e:
                print(f"Error loading token.json: {e}. Re-authenticating.")
                self.creds = None

        if self.creds and not self.creds.has_scopes(SCOPES):
            print("Gmail token is missing required scopes. Re-authenticating.")
            self.creds = None

        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request()) # No need for try-except here, let it propagate if it fails
            else:
                if not os.path.exists(credentials_path):
                    raise FileNotFoundError(
                        f"Missing {credentials_path}. Please download it from Google Cloud Console."
                    )
                flow = InstalledAppFlow.from_client_secrets_file(
                    credentials_path, SCOPES)
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
