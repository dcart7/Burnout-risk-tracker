# Burnout Risk Tracker


## Структура проекта

- `/frontend`: React-приложение (Vite). Использует `.env` для настройки URL API.
- `/backend`: Django REST API. Основная логика и база данных.

---

## Настройка для разработки

### 1. Бэкенд (Django)

1. Перейдите в папку:
   ```bash
   cd backend
   ```
2. Создайте и активируйте виртуальное окружение:
   ```bash
   python -m venv venv
   source venv/bin/activate  # На Windows: venv\Scripts\activate
   ```
3. Установите зависимости:
   ```bash
   pip install -r requirements.txt
   ```
4. Создайте файл `.env`, скопировав `.env.example`, и настройте его.
5. Выполните миграции:
   ```bash
   python manage.py migrate
   ```
6. Запустите сервер:
   ```bash
   python manage.py runserver
   ```

### Банк вопросов (фиксированный, не через HR API)

- Источник вопросов в репозитории:
  - `backend/surveys/fixtures/questions.csv` (рекомендуется для редактирования)
  - `backend/surveys/fixtures/questions.json` (fixture для `loaddata`)
- Формат CSV:
  - `text,category,is_active`
  - `category`: `stress`, `workload`, `motivation`, `energy`
  - `is_active`: `true` или `false` (опционально, по умолчанию `true`)

Импорт CSV в БД:
```bash
cd backend
./venv/bin/python manage.py import_questions surveys/fixtures/questions.csv
```

Полная замена банка вопросов:
```bash
cd backend
./venv/bin/python manage.py import_questions surveys/fixtures/questions.csv --replace
```

Загрузка fixture JSON:
```bash
cd backend
./venv/bin/python manage.py loaddata surveys/fixtures/questions.json
```

### 2. Фронтенд (React)

1. Перейдите в папку:
   ```bash
   cd frontend
   ```
2. Установите зависимости:
   ```bash
   npm install
   ```
3. Создайте файл `.env`, скопировав `.env.example`. По умолчанию `VITE_API_URL` настроен на `http://localhost:8000`.
4. Запустите dev-сервер:
   ```bash
   npm run dev
   ```

## API Документация (текущая)

- `GET /api/hello/` - Тестовый эндпоинт, возвращает "Hello from Django".
- `GET /api/questions/pool/` - Пул активных вопросов для авторизованных пользователей.
- `POST /api/weekly-surveys/submit/` - Отправка weekly survey (8 ответов по активному шаблону, score 0..10).

### Alert System (Day 9)

- При каждом новом `WeeklyScore` запускается фоновая задача генерации алертов.
- Генерируются типы алертов:
  - `spike`: рост `burnout_index_stable` больше 15% относительно предыдущего значения пользователя.
  - `threshold`: `burnout_index_stable` больше 60.
- Повторные алерты одного и того же типа для одного weekly score не дублируются.

Запуск Celery worker:
```bash
cd backend
celery -A core worker -l info
```

Запуск Celery beat (периодический пересчёт алертов):
```bash
cd backend
celery -A core beat -l info
```

Пример `POST /api/weekly-surveys/submit/`:
```json
{
  "answers": [
    { "question_id": 1, "score": 7 },
    { "question_id": 2, "score": 8 },
    { "question_id": 3, "score": 6 },
    { "question_id": 4, "score": 7 },
    { "question_id": 5, "score": 9 },
    { "question_id": 6, "score": 8 },
    { "question_id": 7, "score": 7 },
    { "question_id": 8, "score": 6 }
  ]
}
```

---

## Советы по совместной работе

1. **API First:** Перед реализацией новой фичи, договоритесь о структуре JSON в API.
2. **Environment Variables:** Не коммитьте `.env` файлы. Используйте `.env.example` для описания необходимых переменных.
3. **CORS:** В `backend/core/settings.py` уже настроен `corsheaders`, чтобы фронтенд мог обращаться к бэкенду.
