"""Ручной прогон суммаризатора без ожидания недели.
Запуск: uv run test_summary.py

Идея: сдвигаем "сегодня" вперёд так, чтобы УЖЕ накопленные сообщения
попали в окно "прошлой недели". Окно = пн-вс недели, предшествующей today.
"""
import asyncio
from datetime import date, timedelta

from src.logger import setup_logger
from src.agents.summary_graph import summary_graph_builder
from src.agents.summary_agent import run_weekly_summary

setup_logger()


async def main():
    graph = summary_graph_builder()

    # Берём сегодня + 7 дней: тогда "прошлая неделя" для алгоритма —
    # это ТЕКУЩАЯ реальная неделя, где лежат твои свежие тестовые сообщения.
    fake_today = date.today() + timedelta(days=7)
    print(f"Тестовое 'сегодня': {fake_today} → окно сводки = эта реальная неделя")

    await run_weekly_summary(graph, today=fake_today)


if __name__ == "__main__":
    asyncio.run(main())