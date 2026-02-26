# Burnout Risk Tracker

This project consists of a React frontend and a Django backend.

## Structure

- `/frontend`: React application (Vite)
- `/backend`: Django REST API

## Getting Started

### Backend

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Activate the virtual environment:
   ```bash
   source venv/bin/activate
   ```
3. (Optional) Install dependencies if not already:
   ```bash
   pip install django djangorestframework django-cors-headers
   ```
4. Run migrations:
   ```bash
   python manage.py migrate
   ```
5. Start the server:
   ```bash
   python manage.py runserver
   ```

### Frontend

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Start the development server:
   ```bash
   npm run dev
   ```

## API Endpoints

- `GET /api/hello/`: Returns a hello message from the backend.
