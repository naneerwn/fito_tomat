import pytest
from rest_framework import status
from django.utils import timezone
from diagnostics.models import Disease, Diagnosis, Image
from operations.models import Recommendation, Task


@pytest.mark.django_db
def test_recommendation_crud_full_cycle(api_client, agronomist_user, operator_user, admin_user):
    """
    Тест полного CRUD цикла для рекомендаций.
    """
    # Подготовка данных
    img = Image.objects.create(user=operator_user, file_path="f.jpg", file_format="jpg", timestamp=timezone.now())
    dis = Disease.objects.create(name="D1", description="..", symptoms="..")
    diag = Diagnosis.objects.create(image=img, disease=dis, confidence=0.8)

    # 1. CREATE - Агроном создает рекомендацию
    api_client.force_authenticate(user=agronomist_user)
    data = {
        'diagnosis': diag.id,
        'agronomist': agronomist_user.id,
        'treatment_plan_text': 'Water it',
        'status': 'New'
    }
    response = api_client.post('/api/recommendations/', data)
    assert response.status_code == status.HTTP_201_CREATED
    rec_id = response.data['id']

    # 2. READ - Чтение списка рекомендаций
    response = api_client.get('/api/recommendations/')
    assert response.status_code == status.HTTP_200_OK
    assert response.data['count'] >= 1

    # 3. READ - Чтение детальной информации
    api_client.force_authenticate(user=operator_user)
    response = api_client.get(f'/api/recommendations/{rec_id}/')
    assert response.status_code == status.HTTP_200_OK
    assert response.data['treatment_plan_text'] == 'Water it'

    # 4. UPDATE - Агроном обновляет рекомендацию
    api_client.force_authenticate(user=agronomist_user)
    response = api_client.patch(f'/api/recommendations/{rec_id}/', {'treatment_plan_text': 'Updated plan'})
    assert response.status_code == status.HTTP_200_OK
    assert response.data['treatment_plan_text'] == 'Updated plan'

    # 5. Оператор не может удалять рекомендации -> 403
    api_client.force_authenticate(user=operator_user)
    response = api_client.delete(f'/api/recommendations/{rec_id}/')
    assert response.status_code == status.HTTP_403_FORBIDDEN

    # 6. DELETE - Админ удаляет рекомендацию
    api_client.force_authenticate(user=admin_user)
    response = api_client.delete(f'/api/recommendations/{rec_id}/')
    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert not Recommendation.objects.filter(id=rec_id).exists()


@pytest.mark.django_db
def test_recommendation_creates_task(api_client, agronomist_user, operator_user):
    """
    Тест: При создании рекомендации с operator_id и deadline автоматически создается задача.
    """
    img = Image.objects.create(user=operator_user, file_path="f.jpg", file_format="jpg", timestamp=timezone.now())
    dis = Disease.objects.create(name="D1", description="..", symptoms="..")
    diag = Diagnosis.objects.create(image=img, disease=dis, confidence=0.8)

    api_client.force_authenticate(user=agronomist_user)
    data = {
        'diagnosis': diag.id,
        'agronomist': agronomist_user.id,
        'treatment_plan_text': 'Water it',
        'status': 'New',
        'operator_id': operator_user.id,
        'deadline': (timezone.now() + timezone.timedelta(days=7)).isoformat(),
        'task_description': 'Test task description'
    }
    response = api_client.post('/api/recommendations/', data)
    assert response.status_code == status.HTTP_201_CREATED
    rec_id = response.data['id']

    # Проверяем, что задача была создана
    task = Task.objects.filter(recommendation_id=rec_id, operator=operator_user).first()
    assert task is not None
    assert task.description == 'Test task description'
    assert task.status == 'Назначена'


@pytest.mark.django_db
def test_task_crud_full_cycle(api_client, agronomist_user, operator_user, admin_user):
    """
    Тест полного CRUD цикла для задач.
    """
    # Подготовка данных
    img = Image.objects.create(user=operator_user, file_path="t.jpg", file_format="jpg", timestamp=timezone.now())
    disease = Disease.objects.create(name="Фитофтороз", description="..", symptoms="..")
    diagnosis = Diagnosis.objects.create(image=img, disease=disease, confidence=0.95)
    rec = Recommendation.objects.create(
        diagnosis=diagnosis,
        agronomist=agronomist_user,
        treatment_plan_text="Plan",
        status="New"
    )

    # 1. CREATE - Агроном создает задачу
    api_client.force_authenticate(user=agronomist_user)
    data = {
        'recommendation': rec.id,
        'operator': operator_user.id,
        'description': 'Test task',
        'status': 'Назначена',
        'deadline': (timezone.now() + timezone.timedelta(days=1)).isoformat()
    }
    response = api_client.post('/api/tasks/', data)
    assert response.status_code == status.HTTP_201_CREATED
    task_id = response.data['id']

    # 2. READ - Оператор читает свои задачи
    api_client.force_authenticate(user=operator_user)
    response = api_client.get('/api/tasks/')
    assert response.status_code == status.HTTP_200_OK
    assert response.data['count'] >= 1

    # 3. READ - Чтение детальной информации
    response = api_client.get(f'/api/tasks/{task_id}/')
    assert response.status_code == status.HTTP_200_OK
    assert response.data['description'] == 'Test task'

    # 4. UPDATE - Оператор обновляет статус
    response = api_client.patch(f'/api/tasks/{task_id}/', {'status': 'В работе'})
    assert response.status_code == status.HTTP_200_OK
    assert response.data['status'] == 'В работе'

    # 5. Оператор не может создавать задачи -> 403
    response = api_client.post('/api/tasks/', data)
    assert response.status_code == status.HTTP_403_FORBIDDEN

    # 6. DELETE - Агроном удаляет задачу
    api_client.force_authenticate(user=agronomist_user)
    response = api_client.delete(f'/api/tasks/{task_id}/')
    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert not Task.objects.filter(id=task_id).exists()


@pytest.mark.django_db
def test_operator_can_update_status(api_client, operator_user, agronomist_user):
    """Оператор меняет статус задачи"""
    img = Image.objects.create(user=operator_user, file_path="t.jpg", file_format="jpg", timestamp=timezone.now())
    disease = Disease.objects.create(name="Фитофтороз", description="..", symptoms="..")
    diagnosis = Diagnosis.objects.create(image=img, disease=disease, confidence=0.95)
    rec = Recommendation.objects.create(
        diagnosis=diagnosis,
        agronomist=agronomist_user,
        treatment_plan_text="Plan",
        status="New"
    )
    task = Task.objects.create(
        recommendation=rec,
        operator=operator_user,
        description="Исходное описание",
        status="Назначена",
        deadline=timezone.now(),
    )

    api_client.force_authenticate(user=operator_user)
    response = api_client.patch(f'/api/tasks/{task.id}/', {'status': 'В работе'})
    assert response.status_code == status.HTTP_200_OK
    task.refresh_from_db()
    assert task.status == 'В работе'


@pytest.mark.django_db
def test_operator_cannot_change_description(api_client, operator_user, agronomist_user):
    """Оператор не может менять описание (только статус)"""
    img = Image.objects.create(user=operator_user, file_path="t.jpg", file_format="jpg", timestamp=timezone.now())
    disease = Disease.objects.create(name="Фитофтороз", description="..", symptoms="..")
    diagnosis = Diagnosis.objects.create(image=img, disease=disease, confidence=0.95)
    rec = Recommendation.objects.create(
        diagnosis=diagnosis,
        agronomist=agronomist_user,
        treatment_plan_text="Plan",
        status="New"
    )
    task = Task.objects.create(
        recommendation=rec,
        operator=operator_user,
        description="Исходное описание",
        status="Назначена",
        deadline=timezone.now(),
    )

    api_client.force_authenticate(user=operator_user)
    data = {'description': 'Hacked', 'status': 'Выполнена'}
    response = api_client.patch(f'/api/tasks/{task.id}/', data)
    assert response.status_code == status.HTTP_200_OK
    task.refresh_from_db()
    assert task.status == 'Выполнена'
    assert task.description == "Исходное описание"  # Описание не изменилось
