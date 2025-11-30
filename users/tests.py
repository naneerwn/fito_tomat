import pytest
from rest_framework import status
from django.contrib.auth import get_user_model
from .models import Role

User = get_user_model()


@pytest.mark.django_db
def test_user_list_visibility(api_client, admin_user, operator_user, operator_user_2):
    """
    Тест: Админ видит всех пользователей, Оператор - только себя.
    """
    # 1. Админ запрашивает список
    api_client.force_authenticate(user=admin_user)
    response = api_client.get('/api/users/')
    assert response.status_code == status.HTTP_200_OK
    # Должен видеть: себя, 2-х операторов (всего >= 3)
    assert response.data['count'] >= 3

    # 2. Оператор запрашивает список
    api_client.force_authenticate(user=operator_user)
    response = api_client.get('/api/users/')
    assert response.status_code == status.HTTP_200_OK
    # Должен видеть только одну запись (себя)
    assert response.data['count'] == 1
    assert response.data['results'][0]['username'] == operator_user.username


@pytest.mark.django_db
def test_user_detail_read(api_client, admin_user, operator_user):
    """
    Тест: Чтение детальной информации о пользователе.
    """
    # Оператор может читать свою информацию
    api_client.force_authenticate(user=operator_user)
    response = api_client.get(f'/api/users/{operator_user.id}/')
    assert response.status_code == status.HTTP_200_OK
    assert response.data['username'] == operator_user.username

    # Админ может читать информацию о любом пользователе
    api_client.force_authenticate(user=admin_user)
    response = api_client.get(f'/api/users/{operator_user.id}/')
    assert response.status_code == status.HTTP_200_OK
    assert response.data['username'] == operator_user.username


@pytest.mark.django_db
def test_user_me_endpoint(api_client, operator_user, admin_user):
    """
    Тест: Эндпоинт /api/users/me/ возвращает информацию о текущем пользователе.
    """
    # Оператор
    api_client.force_authenticate(user=operator_user)
    response = api_client.get('/api/users/me/')
    assert response.status_code == status.HTTP_200_OK
    assert response.data['username'] == operator_user.username

    # Админ
    api_client.force_authenticate(user=admin_user)
    response = api_client.get('/api/users/me/')
    assert response.status_code == status.HTTP_200_OK
    assert response.data['username'] == admin_user.username


@pytest.mark.django_db
def test_create_user_permissions(api_client, admin_user, operator_user, role_operator):
    """
    Тест: Только Админ может создавать новых пользователей.
    """
    data = {
        'username': 'new_user', 
        'password': 'password123',
        'full_name': 'New User Test',
        'role': role_operator.id
    }

    # Оператор пытается создать -> 403 Forbidden
    api_client.force_authenticate(user=operator_user)
    response = api_client.post('/api/users/', data)
    assert response.status_code == status.HTTP_403_FORBIDDEN

    # Админ пытается создать -> 201 Created
    api_client.force_authenticate(user=admin_user)
    response = api_client.post('/api/users/', data)
    assert response.status_code == status.HTTP_201_CREATED
    assert User.objects.filter(username='new_user').exists()


@pytest.mark.django_db
def test_update_user_permissions(api_client, admin_user, operator_user, role_operator):
    """
    Тест: Только Админ может обновлять пользователей.
    """
    # Оператор пытается обновить -> 403 Forbidden
    api_client.force_authenticate(user=operator_user)
    response = api_client.patch(f'/api/users/{operator_user.id}/', {'full_name': 'Hacked Name'})
    assert response.status_code == status.HTTP_403_FORBIDDEN

    # Админ обновляет -> 200 OK
    api_client.force_authenticate(user=admin_user)
    response = api_client.patch(f'/api/users/{operator_user.id}/', {'full_name': 'Updated Name'})
    assert response.status_code == status.HTTP_200_OK
    operator_user.refresh_from_db()
    assert operator_user.full_name == 'Updated Name'


@pytest.mark.django_db
def test_delete_user_permissions(api_client, admin_user, operator_user, role_operator):
    """
    Тест: Только Админ может удалять пользователей.
    """
    # Создаем пользователя для удаления
    user_to_delete = User.objects.create_user(
        username='to_delete',
        password='password',
        role=role_operator
    )

    # Оператор пытается удалить -> 403 Forbidden
    api_client.force_authenticate(user=operator_user)
    response = api_client.delete(f'/api/users/{user_to_delete.id}/')
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert User.objects.filter(id=user_to_delete.id).exists()

    # Админ удаляет -> 204 No Content
    api_client.force_authenticate(user=admin_user)
    response = api_client.delete(f'/api/users/{user_to_delete.id}/')
    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert not User.objects.filter(id=user_to_delete.id).exists()


# --- ROLE TESTS ---

@pytest.mark.django_db
def test_role_crud_full_cycle(api_client, admin_user, operator_user):
    """
    Тест полного цикла CRUD для Ролей.
    """
    # 1. CREATE (Админ создает роль)
    api_client.force_authenticate(user=admin_user)
    data = {'name': 'Test Role'}
    response = api_client.post('/api/roles/', data)
    assert response.status_code == status.HTTP_201_CREATED
    role_id = response.data['id']

    # 2. READ (Админ читает роль)
    response = api_client.get(f'/api/roles/{role_id}/')
    assert response.status_code == status.HTTP_200_OK
    assert response.data['name'] == 'Test Role'

    # 3. Оператор пытается создать роль -> 403
    api_client.force_authenticate(user=operator_user)
    response = api_client.post('/api/roles/', {'name': 'Hacked Role'})
    assert response.status_code == status.HTTP_403_FORBIDDEN

    # 4. UPDATE (Админ обновляет роль)
    api_client.force_authenticate(user=admin_user)
    response = api_client.patch(f'/api/roles/{role_id}/', {'name': 'Updated Role Name'})
    assert response.status_code == status.HTTP_200_OK
    assert response.data['name'] == 'Updated Role Name'

    # 5. DELETE (Админ удаляет роль)
    response = api_client.delete(f'/api/roles/{role_id}/')
    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert not Role.objects.filter(id=role_id).exists()


@pytest.mark.django_db
def test_role_list_read(api_client, admin_user, operator_user):
    """
    Тест: Только Админ может читать список ролей.
    """
    Role.objects.create(name='Role 1')
    Role.objects.create(name='Role 2')

    # Оператор пытается прочитать -> 403
    api_client.force_authenticate(user=operator_user)
    response = api_client.get('/api/roles/')
    assert response.status_code == status.HTTP_403_FORBIDDEN

    # Админ читает -> 200 OK
    api_client.force_authenticate(user=admin_user)
    response = api_client.get('/api/roles/')
    assert response.status_code == status.HTTP_200_OK
    assert response.data['count'] >= 2