from sqlalchemy import Integer, String, JSON, Boolean
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class LocalRawMessages(Base):
    __tablename__ = 'lcrwmsgs'

    id: Mapped[int] = mapped_column(primary_key=True)
    author_name: Mapped[str] = mapped_column(String)
    author_username: Mapped[str] = mapped_column(String)
    caption: Mapped[str | None]
    content: Mapped[str | None]
    created_at: Mapped[str] = mapped_column(String)
    file_mime_type: Mapped[str | None]
    file_name: Mapped[str | None]
    file_path: Mapped[str | None]
    forwarded_create_data: Mapped[str | None]
    forwarded_msg_info: Mapped[str | None]
    msg_status: Mapped[str | None]
    message_thread: Mapped[str] = mapped_column(String)
    msg_type: Mapped[str] = mapped_column(String)
    tlg_msg_id: Mapped[int] = mapped_column(Integer)
    session_id: Mapped[int] = mapped_column(Integer)
    session_status: Mapped[str] = mapped_column(String)

    def __repr__(self) -> str:
        message = f"RAW_Сообщение(От={self.author_name}, Сессия={self.session_id!r}, Тип={self.msg_type!r}, Тред={self.message_thread!r})"
        return message + f' Content={self.content[:25]}' if self.content else message


class AssembledMessages(Base):
    __tablename__ = 'asmbld_messages'

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(Integer)
    message_thread: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, default="ready")
    created_at: Mapped[str] = mapped_column(String)
    author_name: Mapped[str | None] = mapped_column(String)

    # Pass 1 — общие поля
    title: Mapped[str | None] = mapped_column(String)
    summary: Mapped[str | None] = mapped_column(String)
    content: Mapped[str | None] = mapped_column(String)
    tags: Mapped[list | None] = mapped_column(JSON, default=None)
    people_mentioned: Mapped[list | None] = mapped_column(JSON, default=None)
    attachments: Mapped[list | None] = mapped_column(JSON, default=None)
    raw_content: Mapped[str] = mapped_column(String)

    # Pass 1 — поиск связанных заметок
    embedding: Mapped[list | None] = mapped_column(JSON, default=None)
    related: Mapped[list | None] = mapped_column(JSON, default=None)
    obsidian_path: Mapped[str | None] = mapped_column(String)

    # calendar-specific
    event_time: Mapped[str | None] = mapped_column(String)
    event_end_time: Mapped[str | None] = mapped_column(String)
    location: Mapped[str | None] = mapped_column(String)
    is_recurring: Mapped[bool | None] = mapped_column(Boolean)
    google_calendar_link: Mapped[str | None] = mapped_column(String)

    # task-specific
    deadline: Mapped[str | None] = mapped_column(String)
    is_done: Mapped[bool | None] = mapped_column(Boolean)
    priority: Mapped[str | None] = mapped_column(String)


class Person(Base):
    __tablename__ = 'persons'

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String)
    telegram_id: Mapped[int | None] = mapped_column(Integer)
    obsidian_path: Mapped[str | None] = mapped_column(String)
    role: Mapped[str | None] = mapped_column(String)
    notes: Mapped[str | None] = mapped_column(String)
    first_seen: Mapped[str] = mapped_column(String)
    last_seen: Mapped[str] = mapped_column(String)