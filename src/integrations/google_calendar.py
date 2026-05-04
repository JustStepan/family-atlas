from datetime import datetime, timedelta
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from src.config import settings
from src.logger import logger

SCOPES = ["https://www.googleapis.com/auth/calendar.events"]


def get_credentials() -> Credentials:
    """Загружает токен, при необходимости обновляет или запускает OAuth flow."""
    token_path: Path = settings.GOOGLE_TOKEN_FILE
    creds_path: Path = settings.GOOGLE_CREDENTIALS_FILE

    creds = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(creds_path), SCOPES)
            creds = flow.run_local_server(port=0)
        token_path.write_text(creds.to_json())

    return creds


def _parse_dt(value: str) -> datetime:
    """Парсит datetime из строки — с секундами или без."""
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    raise ValueError(f"Неизвестный формат datetime: {value!r}")


def create_calendar_event(
    title: str,
    event_time: str,
    event_end_time: str | None = None,
    description: str | None = None,
) -> str | None:
    try:
        service = build(
            "calendar", "v3",
            credentials=get_credentials(),
            cache_discovery=False,  # убирает предупреждение file_cache
        )

        start_dt = _parse_dt(event_time)
        end_dt = _parse_dt(event_end_time) if event_end_time else start_dt + timedelta(hours=1)

        event = {
            "summary": title,
            "description": description or "",
            "start": {"dateTime": start_dt.isoformat(), "timeZone": "Europe/Moscow"},
            "end": {"dateTime": end_dt.isoformat(), "timeZone": "Europe/Moscow"},
        }

        result = service.events().insert(
            calendarId=settings.GOOGLE_CALENDAR_ID,
            body=event,
        ).execute()

        link = result.get("htmlLink")
        logger.info(f"Событие создано в Google Calendar: {title} → {link}")
        return link

    except HttpError as e:
        logger.error(f"Google Calendar API error: {e}")
        return None
    except Exception as e:
        logger.error(f"Ошибка создания события в Google Calendar: {e}")
        return None