from enum import Enum

from sqlalchemy import Integer, String, JSON, Enum as SAEnum
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class AssembledSessionStatus(Enum):
    READY = 'ready'
    DONE = 'done'
    ERROR = 'error'
    PROCESSING = 'processing'


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
    summary: Mapped[str | None] = mapped_column(String)
    obsidian_path: Mapped[str | None] = mapped_column(String)
    tags: Mapped[list | None] = mapped_column(JSON, default=None)
    status: Mapped[AssembledSessionStatus] = mapped_column(
        SAEnum(AssembledSessionStatus),
        default=AssembledSessionStatus.READY
    )
    raw_content: Mapped[str] = mapped_column(String)
    content: Mapped[str | None] = mapped_column(String)
    session_id: Mapped[int] = mapped_column(Integer)
    message_thread: Mapped[str] = mapped_column(String)