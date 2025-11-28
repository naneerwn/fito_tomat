import json
from pathlib import Path

import pytest
from django.utils import timezone
from diagnostics.models import Disease, Diagnosis, Image
from operations.models import Recommendation, Task


# Локальная фикстура для создания задачи
@pytest.fixture
def task_setup(db, agronomist_user, operator_user):
    img = Image.objects.create(user=agronomist_user, file_path="t.jpg", file_format="jpg", timestamp=timezone.now())
    disease = Disease.objects.create(name="Фитофтороз", description="..", symptoms="..")
    diagnosis = Diagnosis.objects.create(image=img, disease=disease, confidence=0.95)
    rec = Recommendation.objects.create(diagnosis=diagnosis, agronomist=agronomist_user, treatment_plan_text="Plan",
                                        status="New")

    task = Task.objects.create(
        recommendation=rec,
        operator=operator_user,
        description="Исходное описание",
        status="New",
        deadline=timezone.now(),
    )
    return task


@pytest.fixture
def reports_tmp_dir(tmp_path, settings):
    settings.REPORTS_DIR = tmp_path
    return tmp_path


@pytest.mark.django_db
def test_operator_can_update_status(api_client, operator_user, task_setup):
    """Оператор меняет статус задачи"""
    api_client.force_authenticate(user=operator_user)

    response = api_client.patch(f'/api/tasks/{task_setup.id}/', {'status': 'In Progress'})

    assert response.status_code == 200
    task_setup.refresh_from_db()
    assert task_setup.status == 'In Progress'


@pytest.mark.django_db
def test_operator_cannot_change_description(api_client, operator_user, task_setup):
    """Оператор не может менять описание (только статус)"""
    api_client.force_authenticate(user=operator_user)

    data = {'description': 'Hacked', 'status': 'Done'}
    response = api_client.patch(f'/api/tasks/{task_setup.id}/', data)

    assert response.status_code == 200
    task_setup.refresh_from_db()
    assert task_setup.status == 'Done'
    assert task_setup.description == "Исходное описание"


@pytest.mark.django_db
def test_recommendation_crud(api_client, agronomist_user, operator_user):
    """
    Тест: Агроном создает рекомендации, Оператор только читает.
    """
    img = Image.objects.create(user=operator_user, file_path="f.jpg", file_format="jpg", timestamp=timezone.now())
    dis = Disease.objects.create(name="D1", description="..", symptoms="..")
    diag = Diagnosis.objects.create(image=img, disease=dis, confidence=0.8)

    api_client.force_authenticate(user=agronomist_user)
    data = {
        'diagnosis': diag.id,
        'agronomist': agronomist_user.id,
        'treatment_plan_text': 'Water it',
        'status': 'New'
    }
    response = api_client.post('/api/recommendations/', data)
    assert response.status_code == 201
    rec_id = response.data['id']

    api_client.force_authenticate(user=operator_user)
    response = api_client.get(f'/api/recommendations/{rec_id}/')
    assert response.status_code == 200

    response = api_client.delete(f'/api/recommendations/{rec_id}/')
    assert response.status_code == 403  # (или 405, если метод запрещен)


@pytest.mark.django_db
def test_report_generation(api_client, agronomist_user, operator_user, reports_tmp_dir):
    """
    Генерация отчета должна возвращать агрегированные данные и сохранять файл.
    """
    img = Image.objects.create(user=operator_user, file_path="rep.jpg", file_format="jpg", timestamp=timezone.now())
    disease = Disease.objects.create(name="Test disease", description="desc", symptoms="symp")
    diag = Diagnosis.objects.create(image=img, disease=disease, confidence=0.88)
    recommendation = Recommendation.objects.create(diagnosis=diag, agronomist=agronomist_user, treatment_plan_text="Plan", status="New")
    Task.objects.create(
        recommendation=recommendation,
        operator=operator_user,
        description="Task",
        status="New",
        deadline=timezone.now() + timezone.timedelta(days=1),
    )

    api_client.force_authenticate(user=agronomist_user)
    payload = {
        'report_type': 'diagnostics_summary',
        'period_start': (timezone.now() - timezone.timedelta(days=1)).isoformat(),
        'period_end': (timezone.now() + timezone.timedelta(days=1)).isoformat(),
    }
    response = api_client.post('/api/reports/', payload, format='json')
    assert response.status_code == 201
    assert response.data['data']['diagnostics']['total'] == 1
    assert response.data['file_path']
    stored_file = Path(response.data['file_path'])
    assert stored_file.exists()
    content = json.loads(stored_file.read_text(encoding='utf-8'))
    assert content['diagnostics']['total'] == 1


@pytest.mark.django_db
def test_audit_log_records_actions(api_client, admin_user):
    api_client.force_authenticate(user=admin_user)
    response = api_client.post('/api/greenhouses/', {'name': 'Audit', 'location': 'Test'})
    assert response.status_code == 201

    response = api_client.get('/api/audit-logs/')
    assert response.status_code == 200
    assert response.data['count'] >= 1
    assert response.data['results'][0]['action_type'] == 'CREATE'