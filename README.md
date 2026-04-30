# Family Atlas

> Персональная система управления семейными знаниями на базе локальных LLM.  
> Telegram → обработка → структурированные заметки в Obsidian.

---

## Что это

Family Atlas собирает голосовые, текстовые и медиа-сообщения из семейного Telegram-форума, обрабатывает их локально через LLM и сохраняет структурированные Markdown-заметки в Obsidian vault.

Проект решает две задачи: реально полезный инструмент для семьи и портфельный проект демонстрирующий практики AI Engineering — локальный инференс, агентные системы, семантический поиск, structured output.

---

## Архитектура

```
Telegram Forum (топики: diary / notes / task / calendar)
    │
    ▼
Telethon Collector
    │  сбор сообщений → LocalRawMessages (SQLite)
    ▼
Assembler
    │  STT (Parakeet TDT 0.6B v3)               ← голосовые → текст
    │  Нормализация STT (GigaChat 3.1 10B)      ← чистка транскрипции
    │  Vision (Qwen3-VL-4B via llama-server)    ← фото → описание
    │  сборка в сессии → AssembledMessages
    ▼
Pass 1 — LangGraph (с LLM)
    analyzer → find_relatives → db_updater
    │
    │  analyzer:       title, summary, tags, content, people_mentioned
    │  find_relatives: BM25 + cosine similarity + LLM verifier
    │  db_updater:     embedding, obsidian_path, related → БД, статус "analyzed"
    ▼
Pass 2 — Python функция (без LLM)
    write_note()
    │
    │  frontmatter + markdown body → .md файл на диске
    │  статус "done"
    ▼
Obsidian Vault
    diary/ notes/ task/ calendar/ persons/
```

---

## Стек

| Слой                | Технологии                                       |
| ------------------- | ------------------------------------------------ |
| Сбор из Telegram    | Telethon                                         |
| База данных         | SQLite + async SQLAlchemy + aiosqlite            |
| LLM инференс        | llama.cpp (`llama-server` как subprocess)        |
| STT                 | Parakeet TDT 0.6B v3 (onnx-asr, CPU)                        |
| Нормализация STT    | GigaChat 3.1 10B A1.8B q6_K                      |
| Vision              | Qwen3-VL-4B-Instruct-Q6_K + mmproj               |
| Агент (Pass 1)      | LangGraph + LangChain (OpenAI-compatible API)    |
| Embeddings          | LaBSE-ru-turbo (sentence-transformers)           |
| Семантический поиск | BM25 (rank-bm25 + pymorphy3) + cosine similarity |
| Frontmatter         | python-frontmatter                               |
| Валидация и конфиг  | Pydantic v2 + pydantic-settings                  |
| Логирование         | Loguru                                           |
| Зависимости         | uv                                               |

---

## Структура проекта

```
familybot/
├── main.py                          # точка входа
├── src/
│   ├── agents/
│   │   ├── graph.py                 # LangGraph граф Pass 1
│   │   ├── nodes.py                 # ноды: analyzer, find_relatives, db_updater
│   │   ├── writer.py                # Pass 2: запись файлов в Obsidian
│   │   ├── obsidian_agent.py        # оркестрация Pass 1 и Pass 2
│   │   └── schemas.py               # FamilyAtlasState + Pydantic output схемы
│   ├── database/
│   │   ├── models.py                # LocalRawMessages, AssembledMessages, Person
│   │   ├── engine.py                # инициализация SQLite
│   │   └── utils.py                 # вспомогательные запросы
│   ├── helpers/
│   │   ├── find_relatives.py        # BM25 + embedding поиск кандидатов
│   │   └── download_models.py       # скачивание embedding модели с HuggingFace
│   ├── infrastructure/
│   │   ├── context.py               # AppContext — lifecycle llama-server
│   │   ├── llm_server.py            # запуск/остановка llama-server subprocess
│   │   └── embeddings.py            # ленивая загрузка LaBSE-ru-turbo
│   ├── msg_assembler/
│   │   ├── assembler.py             # сборка сообщений в сессии
│   │   ├── voice_recognition.py     # STT pipeline: ffmpeg → onnx-asr → нормализация
│   │   ├── image_describer.py       # vision pipeline
│   │   ├── docs_saver.py            # обработка документов и файлов
│   │   └── schemas.py               # VisionOutput
│   ├── msg_collector/
│   │   └── telethon_collector.py    # сбор из Telegram форума
│   ├── prompts/                     # системные промпты для LLM
│   ├── config.py                    # все настройки приложения
│   ├── logger.py                    # настройка Loguru
│   └── utils.py                     # вспомогательные утилиты
├── llm_models/                      # GGUF модели (не в git)
├── logs/                            # логи по дням (не в git)
├── .env
└── pyproject.toml
```

---

## Запуск

### Требования

- Python 3.12+
- `uv`
- `llama-server` в PATH (из llama.cpp)
- `ffmpeg` в PATH (для конвертации аудио)

### Установка

```bash
git clone https://github.com/JustStepan/family-atlas
cd family-atlas
uv sync
cp .env.example .env
# заполни .env своими данными
```

### Переменные окружения `.env`

```env
# Telegram API (получить на my.telegram.org)
TG_API_ID=your_api_id
TG_API_HASH=your_api_hash

# Bot token (BotFather)
BOT_TOKEN=your_bot_token

# ID форума и маппинг участников чата
FORUM_CHAT_ID=-100xxxxxxxxx
FAMILY_CHAT_IDS='{"111111111": "Имя1", "222222222": "Имя2"}'

# Абсолютный путь к Obsidian vault
OBSIDIAN_VAULT_PATH=/path/to/your/obsidian/vault
```

### Настройки в `config.py`

Всё что не меняется между запусками вынесено в `config.py`:

|Параметр|По умолчанию|Описание|
|---|---|---|
|`STT_MODEL`|`nemo-conformer-tdt`|Имя модели для onnx-asr|
|`STT_MODEL_PATH`|`llm_models/stt_models/...`|Путь к STT модели|
|`EMBEDDING_MODEL`|`sergeyzh/LaBSE-ru-turbo`|HuggingFace ID|
|`EMBEDDING_MODEL_PATH`|`llm_models/embeddings/...`|Локальный путь|
|`LLAMA_SERVER_URL`|`http://localhost:8080`|URL llama-server|
|`AGENT_ATTEMPTS`|`2`|Попытки при ошибке LLM|
|`BM25_THRESHHOLD`|`2.0`|Порог BM25 для related|
|`EMBD_THRESHHOLD`|`0.8`|Порог cosine similarity|
|`MSG_SESSION_THRESHOLD`|`{"notes": 5, "diary": 10}`|Минуты между сессиями одного треда|

LLM модели настраиваются в `settings.models` — словарь с именем GGUF файла, аргументами llama-server и `max_tokens`.

### Загрузка моделей

STT и embedding модели скачиваются автоматически:

```bash
uv run src/helpers/download_models.py
```

GGUF модели скачиваются вручную и кладутся в `llm_models/`.

#### Модель агента (основная LLM для анализа заметок)

Минимум — **gpt-oss-20b** (~12 GB RAM):

```
https://huggingface.co/unsloth/gpt-oss-20b-GGUF/blob/main/gpt-oss-20b-Q8_0.gguf
```

Рекомендуется — **Qwen3.6-35B-A3B-APEX-I-Compact** (~17 GB RAM, MoE архитектура):

```
https://huggingface.co/mudler/Qwen3.6-35B-A3B-APEX-GGUF/blob/main/Qwen3.6-35B-A3B-APEX-I-Compact.gguf
```

MoE (Mixture of Experts) — при 35B параметрах активирует только ~3.6B на каждый токен.
Можно использовать и Gemma-4 или экспериментировать с другими моделями. 
После скачивания пропишите в `config.py` в `settings.models`:

```python
"MyAgent": {
    "file": "gpt-oss-20b-Q8_0.gguf",  # имя файла в llm_models/
    "args": [
        "--reasoning-budget", "1024", # сколько токенов модель может потратить на размышления
        "--ctx-size", "16384", # контекстное окно. Можно увеличить при достаточном количестве RAM
    ],
    "max_tokens": 4096, # количество токенов на выходе
},
```

И в `src/agents/obsidian_agent.py` измените:

```python
await ctx.use_model("MyAgent")
```

#### Нормализатор STT (GigaChat — чистка транскрипции, только для русского)

Рекомендуется **GigaChat 3.1 10B A1.8B q6_K** (~8 GB RAM):

```
https://huggingface.co/ai-sage/GigaChat-10B-A1.8B-instruct-GGUF
```

В `config.py` уже настроено:

```python
"GigaChat": {
    "file": "GigaChat3.1-10B-A1.8B-q6_K.gguf",
    "args": [
        "--reasoning", "off",
        "--ctx-size", "16384",
    ],
    "max_tokens": 2048,
},
```

#### Vision модель (описание изображений)

Используется фиксированная модель — менять не рекомендуется.

**Qwen3-VL-4B-Instruct-Q6_K** (~4 GB RAM) + mmproj файл:

```
https://huggingface.co/Qwen/Qwen3-VL-4B-Instruct-GGUF
```

Скачайте оба файла:

- `Qwen3-VL-4B-Instruct-Q6_K.gguf`
- `mmproj-Qwen3-VL-4B-Instruct-F16.gguf`

#### Итоговая структура `llm_models/`

```
llm_models/
├── gpt-oss-20b-Q8_0.gguf                       ← агент
├── GigaChat3.1-10B-A1.8B-q6_K.gguf             ← нормализатор STT
├── Qwen3-VL-4B-Instruct-Q6_K.gguf              ← vision
├── mmproj-Qwen3-VL-4B-Instruct-F16.gguf        ← mmproj для vision
├── embeddings/
│   └── LaBSE-ru-turbo/                         ← скачивается автоматически
└── stt_models/
    └── parakeet-tdt-0.6b-v3-int8/              ← скачивается автоматически
```

### Запуск

```bash
uv run main.py
```

За один запуск программа:

1. Собирает новые сообщения из Telegram форума
2. Обрабатывает медиа (STT, vision) и собирает в сессии
3. Pass 1: анализирует через LLM, ищет связанные заметки, сохраняет в БД
4. Pass 2: записывает Markdown файлы в Obsidian vault

---

## Типы заметок

Telegram форум разделён на топики — каждый соответствует типу заметки:

|Топик|Папка в vault|Описание|
|---|---|---|
|`diary`|`diary/YYYY/MM-месяц/DD-название.md`|Дневниковые записи от первого лица|
|`notes`|`notes/YYYY/MM-месяц/DD-название.md`|Заметки, наблюдения, идеи|
|`task`|`task/YYYY/MM-месяц/WW-неделя.md`|Задачи, группируются по неделям|
|`calendar`|`calendar/YYYY/MM-месяц/DD-название.md`|События с временем и местом|

### Пример frontmatter

```yaml
---
author: СТЕФАН
created: 2026-04-28 15:30:00
thread: diary
tags:
  - богословие
  - семейные_будни
  - покупка_авто
people_mentioned:
  - "[[persons/Женя_менеджер]]"
related:
  - "[[28-Покупка_нового_автомобиля]]"
---
```

---

## Поиск связанных заметок

Трёхуровневый каскад в `find_relatives`:

```
summary текущей заметки
    │
    ├─ BM25 (pymorphy3 лемматизация)      → кандидаты по ключевым словам
    ├─ Cosine similarity (LaBSE-ru-turbo) → кандидаты по смыслу
    │
    └─ UNION → LLM verifier → финальный список стемов related файлов
```

---

## Планируемые улучшения

- [ ] Персоны — карточки `persons/Имя.md` с информацией из заметок
- [ ] Tag drift — нормализация тегов-синонимов через BM25
- [ ] Двусторонние related — обновление frontmatter связанных заметок
- [ ] Еженедельная суммаризация — аудиоотчёты через MOSS-TTS-Nano
- [ ] Docker Compose деплой collector на сервер
- [ ] FastAPI dashboard для мониторинга на localhost

---

## Лицензия

MIT