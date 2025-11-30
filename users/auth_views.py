"""
Кастомные views для JWT аутентификации с документацией для Swagger.
"""
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from drf_spectacular.utils import extend_schema
from drf_spectacular.types import OpenApiTypes


@extend_schema(
    tags=['Аутентификация'],
    summary='Получить JWT токены',
    description='''
    Получение access и refresh токенов для аутентификации в API.
    
    **Параметры запроса:**
    - `username` (обязательный) - имя пользователя
    - `password` (обязательный) - пароль пользователя
    
    **Ответ:**
    - `access` - JWT access токен (действителен 60 минут)
    - `refresh` - JWT refresh токен (действителен 7 дней)
    
    **Использование:**
    После получения токенов, используйте access токен в заголовке Authorization:
    ```
    Authorization: Bearer <access_token>
    ```
    
    Когда access токен истечет, используйте refresh токен для получения нового access токена
    через endpoint `/api/auth/token/refresh/`.
    ''',
    request={
        'application/json': {
            'type': 'object',
            'properties': {
                'username': {'type': 'string', 'description': 'Имя пользователя'},
                'password': {'type': 'string', 'description': 'Пароль пользователя', 'format': 'password'},
            },
            'required': ['username', 'password'],
        }
    },
    responses={
        200: {
            'description': 'Успешная аутентификация',
            'content': {
                'application/json': {
                    'example': {
                        'access': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...',
                        'refresh': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...',
                    }
                }
            }
        },
        401: {
            'description': 'Неверные учетные данные',
            'content': {
                'application/json': {
                    'example': {
                        'detail': 'No active account found with the given credentials'
                    }
                }
            }
        }
    }
)
class CustomTokenObtainPairView(TokenObtainPairView):
    """Получение JWT токенов для аутентификации"""
    pass


@extend_schema(
    tags=['Аутентификация'],
    summary='Обновить access токен',
    description='''
    Обновление access токена с помощью refresh токена.
    
    **Параметры запроса:**
    - `refresh` (обязательный) - refresh токен, полученный при первоначальной аутентификации
    
    **Ответ:**
    - `access` - новый JWT access токен (действителен 60 минут)
    
    **Использование:**
    Когда access токен истечет, отправьте refresh токен на этот endpoint для получения нового access токена.
    Старый refresh токен будет автоматически заменен новым (rotation).
    ''',
    request={
        'application/json': {
            'type': 'object',
            'properties': {
                'refresh': {'type': 'string', 'description': 'Refresh токен'},
            },
            'required': ['refresh'],
        }
    },
    responses={
        200: {
            'description': 'Успешное обновление токена',
            'content': {
                'application/json': {
                    'example': {
                        'access': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...',
                    }
                }
            }
        },
        401: {
            'description': 'Неверный или истекший refresh токен',
            'content': {
                'application/json': {
                    'example': {
                        'detail': 'Token is invalid or expired'
                    }
                }
            }
        }
    }
)
class CustomTokenRefreshView(TokenRefreshView):
    """Обновление JWT access токена"""
    pass

