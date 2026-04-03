from datetime import datetime

from sqlalchemy import Integer, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    id: Mapped[int] = mapped_column(primary_key=True)
    pass


class LocalRawMessages(Base):
    __tablename__ = 'lcrwmsgs'
    
    author_name: Mapped[str] = mapped_column(String)
    author_username: Mapped[str] = mapped_column(String)
    caption: Mapped[str | None]
    content: Mapped[str | None]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    file_id: Mapped[str | None]
    file_mime_type: Mapped[str | None]
    file_name: Mapped[str | None]
    forwarded_create_data: Mapped[str | None]
    forwarded_msg_info: Mapped[str | None]
    message_thread: Mapped[str] = mapped_column(String)
    msg_type: Mapped[str] = mapped_column(String)
    original_id: Mapped[int] = mapped_column(Integer)
    session_id: Mapped[int] = mapped_column(Integer)
    session_status: Mapped[str] = mapped_column(String)

    def __repr__(self) -> str:
        message = f"RAW_Сообщение(От={self.author_name}, Сессия={self.session_id!r}, Тип={self.msg_type!r}, Тред={self.message_thread!r})"
        return message + f' Content={self.content[:25]}' if self.content else message


class AssembledMessages(Base):
    __tablename__ = 'asmbld_messages'
    """Здесь будут сообщения уже подготовленные для работы агента"""
    pass
