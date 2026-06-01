"""Compatibility entrypoint for the Cuby FastAPI app.

Keep this file at the project root so existing commands such as
`uvicorn main:app --reload` continue to work after moving the app code into
the cuby package. It also makes global uvicorn launches use the local venv
packages when the venv exists, which avoids confusing missing-package errors.
"""

from __future__ import annotations

from cuby.bootstrap import prefer_local_venv, restart_with_local_venv_if_needed


if __name__ == "__main__":
    restart_with_local_venv_if_needed(__file__)

prefer_local_venv()

from cuby.main import app  # noqa: E402


if __name__ == "__main__":
    import uvicorn

    from cuby.config import settings

    uvicorn.run(
        "main:app",
        host=settings.SERVER_HOST,
        port=settings.SERVER_PORT,
        reload=False,
    )
