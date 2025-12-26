# АИС "ФитоДиагноз-Томат"

Автоматизированная информационная система диагноcтики заболеваний томата на основе методов распознавания образов.

## Установка

### 1. Клонирование репозитория

```bash
git clone https://github.com/naneerwn/fito_tomato.git
cd fito_tomato
```

### 2. Установка зависимостей

```bash
# Создайте виртуальное окружение
python -m venv venv

# Активируйте виртуальное окружение
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Установите зависимости
pip install -r requirements.txt
```

### 3. ML-модели

Модели находятся в директории `models/`:
- EfficientNet-B3 модель
- Кастомная CNN модель
- Vision Transformer модель
- YOLO11 модель

### 4. Настройка базы данных

Создайте файл `.env` в корне проекта (или используйте переменные окружения):

```env
POSTGRES_DB=fito_tomato
POSTGRES_USER=fito_user
POSTGRES_PASSWORD=your_password
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5432
```

Или для SQLite (для разработки):
```env
USE_SQLITE=1
```

### 5. Применение миграций

```bash
python manage.py migrate
```

### 6. Создание суперпользователя

```bash
python manage.py createsuperuser
```

### 7. Запуск сервера

```bash
python manage.py runserver
```

## Структура проекта

```
fito_tomato/
├── config/              # Настройки Django
├── users/               # Модели пользователей и ролей
├── infrastructure/      # Модели теплиц и секций
├── diagnostics/        # Модели диагностики и ML-сервис
├── operations/         # Модели задач и рекомендаций
├── reports/            # Модели отчётов
├── common/             # Общие утилиты (аудит)
├── frontend/           # React фронтенд
├── docs/               # Документация
└── requirements.txt    # Зависимости Python
```

## Технологии

- **Backend**: Django 5.2, Django REST Framework
- **Frontend**: React, TypeScript, Vite
- **Database**: PostgreSQL
- **ML**: PyTorch, EfficientNet-B3
- **Testing**: pytest, pytest-django

## Лицензия

Проект создан в рамках учебной работы.
