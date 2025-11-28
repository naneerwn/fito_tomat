import pytest
from rest_framework.test import APIClient
from users.models import User, Role

# Фикстура для API клиента
@pytest.fixture
def api_client():
    return APIClient()

# Фикстуры для ролей (создаются один раз)
@pytest.fixture
def role_operator(db):
    return Role.objects.create(name='Оператор')

@pytest.fixture
def role_agronomist(db):
    return Role.objects.create(name='Агроном')

@pytest.fixture
def role_admin(db):
    return Role.objects.create(name='Администратор')

# Фикстуры для пользователей
@pytest.fixture
def operator_user(db, role_operator):
    return User.objects.create_user(username='op1', password='password', role=role_operator)

@pytest.fixture
def operator_user_2(db, role_operator):
    return User.objects.create_user(username='op2', password='password', role=role_operator)

@pytest.fixture
def agronomist_user(db, role_agronomist):
    return User.objects.create_user(username='agro', password='password', role=role_agronomist)

@pytest.fixture
def admin_user(db, role_admin):
    return User.objects.create_superuser(username='admin', password='password', email='a@a.com', role=role_admin)