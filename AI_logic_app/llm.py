import os
import openai
from config import settings as app_settings

# Initialize OpenAI API key from config or environment
api_key = str(app_settings.OPENAI_API_KEY) if getattr(app_settings, 'OPENAI_API_KEY', None) else os.environ.get('OPENAI_API_KEY')
if api_key:
    os.environ.setdefault('OPENAI_API_KEY', api_key)


def generate_response(prompt: str, model: str = "gpt-3.5-turbo") -> str:
    """Generate a short text response from OpenAI chat models.

    Tries to use the new `openai.OpenAI` client (openai>=1.0.0). Falls back
    to the older `openai.ChatCompletion.create` if needed.

    Returns the assistant's reply text or an error message starting with "Error: " on failure.
    """
    if not os.environ.get('OPENAI_API_KEY'):
        return "Error: OpenAI API key not configured"

    # Decide based on installed openai package version: if >=1 use new client API
    try:
        version = getattr(openai, '__version__', '0.0.0')
        major = int(version.split('.')[0]) if version else 0
    except Exception:
        major = 0

    try:
        if major >= 1:
            # Use new OpenAI client
            from openai import OpenAI
            client = OpenAI()
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that answers concisely."},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=400,
                temperature=0.6,
            )
            return resp.choices[0].message.content.strip()
        else:
            # Use old API
            resp = openai.ChatCompletion.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that answers concisely."},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=400,
                temperature=0.6,
            )
            return resp.choices[0].message.content.strip()
    except Exception as exc:
        return f"Error: {exc}"
