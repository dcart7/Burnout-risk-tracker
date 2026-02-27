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

---

## Советы по совместной работе

1. **API First:** Перед реализацией новой фичи, договоритесь о структуре JSON в API.
2. **Environment Variables:** Не коммитьте `.env` файлы. Используйте `.env.example` для описания необходимых переменных.
3. **CORS:** В `backend/core/settings.py` уже настроен `corsheaders`, чтобы фронтенд мог обращаться к бэкенду.
