"""
Настройки Django для проекта config.

Сгенерировано командой 'django-admin startproject' с использованием Django 5.2.8.

Для получения дополнительной информации об этом файле см.
https://docs.djangoproject.com/en/5.2/topics/settings/

Для полного списка настроек и их значений см.
https://docs.djangoproject.com/en/5.2/ref/settings/
"""

from pathlib import Path
from datetime import timedelta
import os

# Построение путей внутри проекта: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-2xtru%o$^d9_n%$qw*%9y$3lr)y1pt8)z&yikb!#k5uwhm2hit'

DEBUG = True

ALLOWED_HOSTS = []


# Определение приложений

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'corsheaders',
    'users',
    'infrastructure',
    'diagnostics',
    'operations',
    'reports',
    'rest_framework',
    'drf_spectacular',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',  # По умолчанию доступ только авторизованным
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.BasicAuthentication',
    ],
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 10,
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'АИС "ФитоДиагноз-Томат" API',
    'DESCRIPTION': '''
    RESTful API для автоматизированной информационной системы диагностики заболеваний томата.
    
    Система использует методы машинного обучения (ML) для автоматического определения заболеваний растений
    на основе анализа изображений. API предоставляет полный функционал для работы с:
    
    - **Пользователями и ролями**: управление пользователями системы и их ролями
    - **Инфраструктурой**: управление теплицами и секциями
    - **Диагностикой**: загрузка изображений, автоматическая ML-диагностика, управление диагнозами и справочником заболеваний
    - **Операциями**: создание рекомендаций по лечению и управление задачами для операторов
    - **Отчетами**: генерация отчетов за указанные периоды и просмотр журнала аудита
    
    ## Аутентификация
    
    API использует JWT (JSON Web Token) аутентификацию. Для получения токена используйте:
    - `POST /api/auth/token/` - получение access и refresh токенов
    - `POST /api/auth/token/refresh/` - обновление access токена
    
    ## Версия API
    
    Текущая версия: 1.0.0
    ''',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    # Настройки для корректного отображения JWT авторизации в Swagger
    'COMPONENT_SPLIT_REQUEST': True,
    'SCHEMA_PATH_PREFIX': '/api',
    'TAGS': [
        {'name': 'Пользователи и роли', 'description': 'Управление пользователями системы и ролями'},
        {'name': 'Инфраструктура', 'description': 'Управление теплицами и секциями'},
        {'name': 'Диагностика', 'description': 'Загрузка изображений, ML-диагностика, управление диагнозами и справочником заболеваний'},
        {'name': 'Операции', 'description': 'Рекомендации по лечению и управление задачами'},
        {'name': 'Отчеты', 'description': 'Генерация отчетов и просмотр журнала аудита'},
        {'name': 'Аутентификация', 'description': 'Получение и обновление JWT токенов'},
    ],
    'CONTACT': {
        'name': 'Поддержка API',
        'email': 'support@fitodiagnoz.local',
    },
    'LICENSE': {
        'name': 'Учебный проект',
    },
}

# База данных
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

USE_SQLITE = os.environ.get('USE_SQLITE', '0') == '1'

if USE_SQLITE:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.environ.get('POSTGRES_DB', 'fito_tomato'),
            'USER': os.environ.get('POSTGRES_USER', 'fito_user'),
            'PASSWORD': os.environ.get('POSTGRES_PASSWORD', 'fito_pass'),
            'HOST': os.environ.get('POSTGRES_HOST', '192.168.56.104'),
            'PORT': os.environ.get('POSTGRES_PORT', '5432'),
        }
    }


# Валидация паролей
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Интернационализация
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'ru-ru'

TIME_ZONE = 'Asia/Yekaterinburg'

USE_I18N = True

USE_TZ = True


# Статические файлы (CSS, JavaScript, Изображения)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = 'static/'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
MEDIA_ROOT.mkdir(parents=True, exist_ok=True)

REPORTS_DIR = BASE_DIR / 'generated_reports'
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

# Настройки ML моделей
ML_MODEL_PATH = BASE_DIR / 'models' / 'EfficientNet-B3_best.pth'
CUSTOM_CNN_MODEL_PATH = BASE_DIR / 'models' / 'best_model.pth'
VIT_MODEL_PATH = BASE_DIR / 'models' / 'ViT-Base_best.pth'
YOLO_MODEL_PATH = BASE_DIR / 'models' / 'best.pt'

# Модель по умолчанию для диагностики (можно изменить через переменную окружения)
# Возможные значения: 'effnet', 'custom_cnn', 'vit', 'yolo'
DEFAULT_ML_MODEL = os.environ.get('DEFAULT_ML_MODEL', 'effnet')

# Точность (accuracy) моделей на тестовом наборе (в процентах)
# Эти значения можно обновить после оценки моделей на тестовом наборе
ML_MODEL_ACCURACIES = {
    'effnet': float(os.environ.get('EFFNET_ACCURACY', '92.5')),  # EfficientNet-B3
    'custom_cnn': float(os.environ.get('CUSTOM_CNN_ACCURACY', '85.0')),  # Custom CNN
    'vit': float(os.environ.get('VIT_ACCURACY', '91.0')),  # Vision Transformer
    'yolo': float(os.environ.get('YOLO_ACCURACY', '88.5')),  # YOLO
}

HEATMAP_DIR = MEDIA_ROOT / 'heatmaps'
HEATMAP_DIR.mkdir(parents=True, exist_ok=True)

CORS_ALLOWED_ORIGINS = [
    'http://localhost:5173',
    'http://127.0.0.1:5173',
]
CORS_ALLOW_CREDENTIALS = True

# Тип поля первичного ключа по умолчанию
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
AUTH_USER_MODEL = 'users.User'
