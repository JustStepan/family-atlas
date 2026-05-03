# Family Atlas

> Персональная система управления семейными знаниями на базе локальных LLM.  
> Telegram → обработка → структурированные заметки в Obsidian.

---

## Что это

Family Atlas собирает голосовые, текстовые и медиа-сообщения из семейного Telegram-форума, обрабатывает их локально через LLM и сохраняет структурированные Markdown-заметки в Obsidian vault. Календарные события автоматически добавляются в Google Calendar.

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
    │  Нормализация STT (GigaChat 3.1 10B)       ← чистка транскрипции
    │  Vision (Qwen3-VL-4B via llama-server)     ← фото → описание
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
    │  calendar: создание события в Google Calendar → ссылка в файл
    │  статус "done"
    ▼
Obsidian Vault
    diary/ notes/ task/ calendar/ persons/
```

---

## Стек

| Слой                | Технологии                                        |
|---------------------|---------------------------------------------------|
| Сбор из Telegram    | Telethon                                          |
| База данных         | SQLite + async SQLAlchemy + aiosqlite             |
| LLM инференс        | llama.cpp (`llama-server` как subprocess)         |
| STT                 | Parakeet TDT 0.6B v3 (onnx-asr, CPU)             |
| Нормализация STT    | GigaChat 3.1 10B A1.8B q6_K                       |
| Vision              | Qwen3-VL-4B-Instruct-Q6_K + mmproj               |
| Агент (Pass 1)      | LangGraph + LangChain (OpenAI-compatible API)     |
| Embeddings          | LaBSE-ru-turbo (sentence-transformers)            |
| Семантический поиск | BM25 (rank-bm25 + pymorphy3) + cosine similarity  |
| Frontmatter         | python-frontmatter                                |
| Календарь           | Google Calendar API (google-api-python-client)    |
| Валидация и конфиг  | Pydantic v2 + pydantic-settings                   |
| Логирование         | Loguru                                            |
| Зависимости         | uv                                                |

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
│   │   └── download_models.py       # скачивание STT и embedding моделей
│   ├── infrastructure/
│   │   ├── context.py               # AppContext — lifecycle llama-server
│   │   ├── llm_server.py            # запуск/остановка llama-server subprocess
│   │   └── embeddings.py            # ленивая загрузка LaBSE-ru-turbo
│   ├── integrations/
│   │   └── google_calendar.py       # создание событий в Google Calendar
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

## Установка

### 1. Системные зависимости

**uv** (менеджер пакетов Python):
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**ffmpeg** (конвертация аудио):
```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt install ffmpeg
```

**llama-server** (локальный LLM инференс):

```bash
# macOS — через brew
brew install llama.cpp
```

Или скачай бинарник с [github.com/ggerganov/llama.cpp/releases](https://github.com/ggerganov/llama.cpp/releases) и добавь `llama-server` в PATH.

Проверь что всё установлено:
```bash
uv --version
ffmpeg -version
llama-server --version
```

### 2. Клонирование и установка зависимостей

```bash
git clone https://github.com/JustStepan/family-atlas
cd family-atlas
uv sync
cp .env.example .env
```

### 3. Настройка `.env`

```env
# Telegram API — получить на https://my.telegram.org
TG_API_ID=your_api_id
TG_API_HASH=your_api_hash

# ID форума и маппинг участников
FORUM_CHAT_ID=-100xxxxxxxxx
FAMILY_CHAT_IDS='{"111111111": "Имя1", "222222222": "Имя2"}'

# Абсолютный путь к Obsidian vault
OBSIDIAN_VAULT_PATH=/path/to/your/obsidian/vault
```

**Как узнать `TG_API_ID` и `TG_API_HASH`:**
зайди на [my.telegram.org](https://my.telegram.org) → API development tools → создай приложение.

**Как узнать `FORUM_CHAT_ID`:**
перешли любое сообщение из форума боту [@userinfobot](https://t.me/userinfobot) — он покажет ID чата.

**Как узнать `user_id` членов семьи для `FAMILY_CHAT_IDS`:**
каждый участник пишет боту [@userinfobot](https://t.me/userinfobot) напрямую — бот возвращает его ID.

### 3.5. Узнай ID топиков форума

ID топиков у каждого форума свои. Запусти скрипт чтобы узнать их:

```bash
uv run src/helpers/get_forum_threads.py
```

Вывод будет примерно такой:

```
Форум: Наша семья
----------------------------------------
ID     Название
----------------------------------------
2      Дневник
4      Календарь
6      Заметки
8      Задачи
```

Открой `src/msg_collector/telethon_collector.py` и обнови `THREAD_MAPS`:

```python
THREAD_MAPS = {
    2: "diary",      # ← твой ID топика "Дневник"
    4: "calendar",   # ← твой ID топика "Календарь"
    6: "notes",      # ← твой ID топика "Заметки"
    8: "task",       # ← твой ID топика "Задачи"
}
```

Значения (`"diary"`, `"calendar"`, `"notes"`, `"task"`) не менять — они определяют тип заметки и путь в Obsidian vault.

### 4. Загрузка моделей

**STT и embedding** — скачиваются автоматически:
```bash
uv run src/helpers/download_models.py
```

**GGUF модели** — скачиваются вручную в папку `llm_models/`. Подробности в разделе [Модели](#модели).

### 5. Google Calendar (опционально)

Если хочешь автоматически добавлять события из топика `calendar`:

1. Создай проект на [console.cloud.google.com](https://console.cloud.google.com)
2. Включи **Google Calendar API**
3. Создай **OAuth 2.0 Client ID** → тип Desktop app → скачай JSON
4. Положи файл в корень проекта как `calendar_credentials.json`

> ⚠️ Добавь оба файла в `.gitignore`: `calendar_credentials.json` и `calendar_token.json`

При первом запуске с calendar-сессией откроется браузер — авторизуйся. Токен сохранится в `calendar_token.json` и будет обновляться автоматически.

Если Google Calendar не настроен — календарные заметки сохранятся в Obsidian без ссылки на событие, ничего не упадёт.

### 6. Первый запуск

```bash
uv run main.py
```

При первом запуске Telethon запросит авторизацию в Telegram — введи номер телефона и код из приложения:

```
Please enter your phone (or bot token): +7XXXXXXXXXX
Please enter the code you received: 12345
```

После авторизации в корне проекта появится файл `family_atlas.session` — кэш сессии, повторная авторизация не потребуется. Файл не попадает в git.

За один запуск программа:

1. Собирает новые сообщения из Telegram форума
2. Обрабатывает медиа (STT, vision) и собирает в сессии
3. Pass 1: анализирует через LLM, ищет связанные заметки, сохраняет в БД
4. Pass 2: записывает Markdown файлы в Obsidian vault, создаёт события в Google Calendar

---

## Настройки в `config.py`

| Параметр                | По умолчанию                    | Описание                              |
|-------------------------|---------------------------------|---------------------------------------|
| `STT_MODEL`             | `nemo-parakeet-tdt-0.6b-v3`     | Имя модели для onnx-asr               |
| `STT_MODEL_PATH`        | `llm_models/stt_models/...`     | Путь к STT модели                     |
| `EMBEDDING_MODEL`       | `sergeyzh/LaBSE-ru-turbo`       | HuggingFace ID                        |
| `EMBEDDING_MODEL_PATH`  | `llm_models/embeddings/...`     | Локальный путь                        |
| `LLAMA_SERVER_URL`      | `http://localhost:8080`         | URL llama-server                      |
| `AGENT_ATTEMPTS`        | `2`                             | Попытки при ошибке LLM                |
| `BM25_THRESHOLD`        | `2.0`                           | Порог BM25 для related                |
| `EMBEDDING_THRESHOLD`   | `0.8`                           | Порог cosine similarity для related   |
| `MSG_SESSION_THRESHOLD` | `{"notes": 5, "diary": 10}`     | Минуты между сессиями одного треда    |
| `GOOGLE_CALENDAR_ID`    | `primary`                       | ID Google календаря                   |

LLM модели настраиваются в `settings.models` — словарь с именем GGUF файла, аргументами llama-server и `max_tokens`.

---

## Модели

### GGUF модели (скачать вручную в `llm_models/`)

**Агент — основная LLM для анализа заметок:**

Минимум — **gpt-oss-20b** (~12 GB / ~16 GB RAM):
```
https://huggingface.co/unsloth/gpt-oss-20b-GGUF/blob/main/gpt-oss-20b-Q8_0.gguf
```

Рекомендуется — **Qwen3.6-35B-A3B-APEX-I-Compact** (~17 GB / ~24 GB RAM, MoE архитектура):
```
https://huggingface.co/mudler/Qwen3.6-35B-A3B-APEX-GGUF/blob/main/Qwen3.6-35B-A3B-APEX-I-Compact.gguf
```

MoE (Mixture of Experts) — при 35B параметрах активирует только ~3.6B на каждый токен. Можно использовать Gemma-4 или другие GGUF модели совместимые с llama-server.

**Нормализатор STT** — только для русского (~8 GB RAM):
```
https://huggingface.co/ai-sage/GigaChat-10B-A1.8B-instruct-GGUF
```
Файл: `GigaChat3.1-10B-A1.8B-q6_K.gguf`

**Vision модель** (~4 GB RAM) — скачай оба файла:
```
https://huggingface.co/Qwen/Qwen3-VL-4B-Instruct-GGUF
```
Файлы: `Qwen3-VL-4B-Instruct-Q6_K.gguf` и `mmproj-Qwen3-VL-4B-Instruct-F16.gguf`

После скачивания агента пропиши в `config.py` в `settings.models` и укажи алиас в `src/agents/obsidian_agent.py`:

```python
# config.py
"MyAgent": {
    "file": "gpt-oss-20b-Q8_0.gguf",
    "args": [
        "--reasoning-budget", "1024",
        "--ctx-size", "16384",
    ],
    "max_tokens": 4096,
},
```

```python
# src/agents/obsidian_agent.py
await ctx.use_model("MyAgent")
```

### Итоговая структура `llm_models/`

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

---

## Типы заметок

| Топик      | Папка в vault                           | Описание                           |
|------------|-----------------------------------------|------------------------------------|
| `diary`    | `diary/YYYY/MM-месяц/DD-название.md`    | Дневниковые записи от первого лица |
| `notes`    | `notes/YYYY/MM-месяц/DD-название.md`    | Заметки, наблюдения, идеи          |
| `task`     | `task/YYYY/MM-месяц/WW-неделя.md`       | Задачи, группируются по неделям    |
| `calendar` | `calendar/YYYY/MM-месяц/DD-название.md` | События с временем и местом        |

### Пример frontmatter

```yaml
---
author: СТЕФАН
created: 2026-04-28 15:30:00
thread: diary
tags:
  - семейные_будни
  - покупка_авто
people_mentioned:
  - "[[persons/Женя_менеджер]]"
related:
  - "[[28-Покупка_нового_автомобиля.md]]"
---
```

---

## Поиск связанных заметок

Трёхуровневый каскад в `find_relatives`:

```
summary текущей заметки
    │
    ├─ BM25 (pymorphy3 лемматизация)       → кандидаты по ключевым словам
    ├─ Cosine similarity (LaBSE-ru-turbo)  → кандидаты по смыслу
    │
    └─ UNION → LLM verifier → финальный список стемов related файлов
```

---

## Планируемые улучшения

- [ ] Персоны — карточки `persons/Имя.md` с информацией из заметок
- [ ] Tag drift — нормализация тегов-синонимов через BM25
- [ ] Двусторонние related — обновление frontmatter связанных заметок
- [ ] Google Calendar link — сохранение ссылки на событие в БД и frontmatter
- [ ] Еженедельная суммаризация — аудиоотчёты через MOSS-TTS-Nano
- [ ] Docker Compose деплой collector на сервер
- [ ] FastAPI dashboard для мониторинга на localhost

---

## Лицензия

MIT