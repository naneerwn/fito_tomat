import pytest
from rest_framework import status
from .models import Greenhouse, Section


# Маркер, указывающий, что тестам нужен доступ к базе данных
@pytest.mark.django_db
class TestInfrastructurePermissions:
    """
    Тестирование прав доступа и CRUD операций для Greenhouses и Sections.
    """

    # --- GREENHOUSE TESTS ---

    def test_greenhouse_create_permissions(self, api_client, admin_user, operator_user):
        """
        Тест: Администратор может создать Теплицу (C), Оператор не может (403).
        """
        data = {'name': 'New Greenhouse', 'location': 'Test Location'}

        # 1. Оператор пытается создать -> Должен быть 403 Forbidden
        api_client.force_authenticate(user=operator_user)
        response = api_client.post('/api/greenhouses/', data)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert Greenhouse.objects.count() == 0

        # 2. Администратор создает -> 201 Created
        api_client.force_authenticate(user=admin_user)
        response = api_client.post('/api/greenhouses/', data)
        assert response.status_code == status.HTTP_201_CREATED
        assert Greenhouse.objects.count() == 1

    def test_greenhouse_read_all(self, api_client, operator_user, admin_user):
        """
        Тест: Все авторизованные пользователи могут просматривать список Теплиц (R).
        """
        # Создаем тестовую теплицу
        Greenhouse.objects.create(name='T1', location='L1')

        # 1. Оператор читает
        api_client.force_authenticate(user=operator_user)
        response = api_client.get('/api/greenhouses/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 1

        # 2. Администратор читает
        api_client.force_authenticate(user=admin_user)
        response = api_client.get('/api/greenhouses/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 1

    def test_greenhouse_update_delete_permissions(self, api_client, admin_user, operator_user):
        """
        Тест: Только Администратор может обновить (U) или удалить (D) Теплицу.
        """
        gh = Greenhouse.objects.create(name='To Update', location='Old Loc')

        # 1. Оператор пытается обновить -> 403
        api_client.force_authenticate(user=operator_user)
        update_data = {'name': 'Hacked Name'}
        response = api_client.patch(f'/api/greenhouses/{gh.id}/', update_data)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        gh.refresh_from_db()
        assert gh.name == 'To Update'  # Имя не должно измениться

        # 2. Администратор обновляет -> 200 OK
        api_client.force_authenticate(user=admin_user)
        update_data = {'name': 'Updated Name'}
        response = api_client.patch(f'/api/greenhouses/{gh.id}/', update_data)
        assert response.status_code == status.HTTP_200_OK
        gh.refresh_from_db()
        assert gh.name == 'Updated Name'

        # 3. Оператор пытается удалить -> 403
        api_client.force_authenticate(user=operator_user)
        response = api_client.delete(f'/api/greenhouses/{gh.id}/')
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert Greenhouse.objects.count() == 1  # Не удалено

        # 4. Администратор удаляет -> 204 No Content
        api_client.force_authenticate(user=admin_user)
        response = api_client.delete(f'/api/greenhouses/{gh.id}/')
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert Greenhouse.objects.count() == 0

    # --- SECTION TESTS ---

    def test_section_crud_full_cycle(self, api_client, admin_user, operator_user):
        """
        Тест полного цикла CRUD для Секций с проверкой прав.
        """
        gh = Greenhouse.objects.create(name="Main House", location="Loc")

        # 1. CREATE (Админ создает секцию)
        api_client.force_authenticate(user=admin_user)
        data = {'name': 'Section A', 'greenhouse': gh.id, 'description': 'Test'}
        response = api_client.post('/api/sections/', data)
        assert response.status_code == status.HTTP_201_CREATED
        section_id = response.data['id']

        # 2. READ (Оператор читает секцию)
        api_client.force_authenticate(user=operator_user)
        response = api_client.get(f'/api/sections/{section_id}/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == 'Section A'

        # 3. UPDATE (Оператор пытается изменить -> 403)
        api_client.force_authenticate(user=operator_user)
        response = api_client.patch(f'/api/sections/{section_id}/', {'name': 'Hacked'})
        assert response.status_code == status.HTTP_403_FORBIDDEN

        # 4. DELETE (Админ удаляет)
        api_client.force_authenticate(user=admin_user)
        response = api_client.delete(f'/api/sections/{section_id}/')
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert Section.objects.count() == 0