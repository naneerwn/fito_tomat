import pytest
from django.contrib.auth import get_user_model
User = get_user_model()

@pytest.mark.django_db
def test_user_list_visibility(api_client, admin_user, operator_user, operator_user_2):
    """
    Тест: Админ видит всех пользователей, Оператор - только себя.
    """
    # 1. Админ запрашивает список
    api_client.force_authenticate(user=admin_user)
    response = api_client.get('/api/users/')
    assert response.status_code == 200
    # Должен видеть: себя, 2-х операторов (всего >= 3)
    assert response.data['count'] >= 3

    # 2. Оператор запрашивает список
    api_client.force_authenticate(user=operator_user)
    response = api_client.get('/api/users/')
    assert response.status_code == 200
    # Должен видеть только одну запись (себя)
    assert response.data['count'] == 1
    assert response.data['results'][0]['username'] == operator_user.username

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
    assert response.status_code == 403

    # Админ пытается создать -> 201 Created
    api_client.force_authenticate(user=admin_user)
    response = api_client.post('/api/users/', data)
    assert response.status_code == 201
    assert User.objects.filter(username='new_user').exists()