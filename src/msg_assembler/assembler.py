import pprint

from sqlalchemy import select

from src.msg_processor.collect_msg import mark_messages_done
from src.database.models import AssembledMessages, LocalRawMessages
from src.msg_assembler.image_describer import process_photo_messages
from src.msg_assembler.voice_recognition import process_voice_messages
from src.database.engine import get_db
from src.logger import logger


async def prepare_msgs():
    async with get_db() as session:
        query = await session.execute(
            select(LocalRawMessages).where(
                LocalRawMessages.session_status == "ready",
            )
        )
        messages = query.scalars().all()

        voice_msgs = [m for m in messages if m.msg_type == "voice"]
        if voice_msgs:
            logger.info(f'Обрабатываем аудио сообщения в количестве: {len(voice_msgs)} шт.')
            voice_msgs = await process_voice_messages(session, voice_msgs)

        photo_msgs = [m for m in messages if m.msg_type == "photo"]
        if photo_msgs:
            logger.info(f'Обрабатываем фото сообщения в количестве: {len(photo_msgs)} шт.')    
            photo_msgs = await process_photo_messages(session, photo_msgs)


        other_msgs = [m for m in messages if m.msg_type in ["document", "video", "text"]]
        if other_msgs:
            logger.info(f'Обрабатываем прочие сообщения в количестве: {len(other_msgs)} шт.')
            for msg in other_msgs:
                msg.msg_status = 'ready'

        msgs_for_assembling = voice_msgs + photo_msgs + other_msgs
        done_ids = await assembler(session, msgs_for_assembling)
        server_result = await mark_messages_done(done_ids)
        # здесь отправка ids на сервер для фиксации результата
        await session.commit()
        return server_result


async def assembler(session, messages) -> list[int]:
    msg_type_map = {
        "voice": "Голосовое сообщение",
        "text": "Текстовое сообщение",
        "photo": "Сообщение, сожержащее фото",
        "video": "Сообщение, сожержащее видео",
        "document": "Сообщение, сожержащее документ",
    }
    last_session_id = 0
    session_data = []

    for msg in messages:
        message_thread = msg.message_thread
        msg_session_id = msg.session_id
        msg_type = msg.msg_type
        content = f'[{msg_type_map[msg_type]} от автора: {msg.author_name}]\n- Содержание: {msg.content}\n- Дата создания сообщения {msg.created_at}'
        
        if forwarded_msg_info := msg.forwarded_msg_info:
            content += f'\n - {forwarded_msg_info}. Оригинальное сообщение было создано {msg.forwarded_create_data}'

        if file_name := msg.file_name:
            content += f'\n- Имя прикрепленного файла {file_name}'

        if caption := msg.caption:
            content += f'\n- Заголовок прикрепленного документа: {caption}'

        if msg_session_id == last_session_id:
            new_data["content"] += f'\n\nЕще одно сообщение для этой темы:\n{content}'
        else:
            new_data = {
                "message_thread": message_thread,
                "content": content,
                "session_id": msg_session_id,
            }

        last_session_id = msg_session_id
        session_data.append(new_data)

    pprint.pprint(session_data)
    for ss in session_data:
        new_session = AssembledMessages(
            content=ss["content"],
            session_id=ss["session_id"],
            message_thread=ss["message_thread"]
        )
        session.add(new_session)

    return [m.original_id for m in messages]