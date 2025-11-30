import pytest
import tempfile
import shutil
from django.test import override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from .models import Image, Disease, Diagnosis
from infrastructure.models import Greenhouse, Section
from PIL import Image as PilImage
import io

# Создаем временную папку для медиа
MEDIA_ROOT = tempfile.mkdtemp()

@pytest.fixture
def test_section_setup(db):
    # Создаем теплицу, т.к. секция зависит от нее
    gh = Greenhouse.objects.create(name='Test GH', location='Loc')
    return Section.objects.create(name='Test Sec', greenhouse=gh)

@pytest.fixture(autouse=True)
def cleanup_media():
    # Этот код выполнится ПОСЛЕ теста (аналог tearDown)
    yield
    shutil.rmtree(MEDIA_ROOT, ignore_errors=True)


@override_settings(MEDIA_ROOT=MEDIA_ROOT)
@pytest.mark.django_db  # Маркер: разрешаем тесту доступ к БД
def test_operator_can_upload_image(api_client, operator_user, test_section_setup):

    api_client.force_authenticate(user=operator_user)

    # --- создаём настоящее JPEG изображение ---
    buffer = io.BytesIO()
    img = PilImage.new("RGB", (100, 100), "red")
    img.save(buffer, format="JPEG")
    buffer.seek(0)

    image_content = SimpleUploadedFile(
        "test.jpg",
        buffer.read(),
        content_type="image/jpeg",
    )

    data = {
        'file_path': image_content,
        'file_format': 'jpg',
        'section': test_section_setup.id,
    }

    response = api_client.post('/api/images/', data, format='multipart')
    print(response.data)  # проверить, что ошибок нет

    assert response.status_code == 201
    assert Image.objects.count() == 1
    assert Image.objects.first().user == operator_user


@pytest.mark.django_db
def test_data_isolation(api_client, operator_user, operator_user_2, agronomist_user):
    """Тест: Изоляция данных. Оператор видит свои, Агроном - все [cite: 142, 143]"""

    # Создаем данные напрямую через ORM
    Image.objects.create(user=operator_user, file_path="img1.jpg", file_format="jpg", timestamp="2025-09-01T12:00:00Z")
    Image.objects.create(user=operator_user_2, file_path="img2.jpg", file_format="jpg",
                         timestamp="2025-09-01T12:00:00Z")

    # 1. Проверка Оператора 1 (должен видеть 1 фото)
    api_client.force_authenticate(user=operator_user)
    response = api_client.get('/api/images/')
    assert response.data['count'] == 1

    # 2. Проверка Агронома (должен видеть 2 фото)
    api_client.force_authenticate(user=agronomist_user)
    response = api_client.get('/api/images/')
    assert response.data['count'] == 2


@pytest.mark.django_db
def test_disease_catalog_permissions(api_client, agronomist_user, operator_user, admin_user):
    """
    Тест: Справочник болезней - полный CRUD.
    """
    # 1. Оператор может ЧИТАТЬ список болезней
    disease = Disease.objects.create(name="Rot", description="...", symptoms="...")
    api_client.force_authenticate(user=operator_user)
    response = api_client.get('/api/diseases/')
    assert response.status_code == 200
    assert response.data['count'] == 1

    # 2. Оператор может читать детальную информацию
    response = api_client.get(f'/api/diseases/{disease.id}/')
    assert response.status_code == 200
    assert response.data['name'] == 'Rot'

    # 3. Оператор НЕ может СОЗДАВАТЬ болезни -> 403
    data = {'name': 'Hacked Disease', 'description': 'Desc', 'symptoms': 'Symp'}
    response = api_client.post('/api/diseases/', data)
    assert response.status_code == 403

    # 4. Агроном может создавать болезни
    api_client.force_authenticate(user=agronomist_user)
    data = {'name': 'New Disease', 'description': 'Desc', 'symptoms': 'Symp'}
    response = api_client.post('/api/diseases/', data)
    assert response.status_code == 201
    new_disease_id = response.data['id']

    # 5. Агроном может обновлять болезни
    response = api_client.patch(f'/api/diseases/{new_disease_id}/', {'description': 'Updated Desc'})
    assert response.status_code == 200
    assert response.data['description'] == 'Updated Desc'

    # 6. Админ может удалять болезни
    api_client.force_authenticate(user=admin_user)
    response = api_client.delete(f'/api/diseases/{new_disease_id}/')
    assert response.status_code == 204
    assert not Disease.objects.filter(id=new_disease_id).exists()


@pytest.mark.django_db
def test_diagnosis_workflow(api_client, agronomist_user, operator_user, admin_user):
    """
    Тест полного CRUD цикла для диагнозов.
    """
    # Подготовка
    disease = Disease.objects.create(name="X", description="D", symptoms="S")
    from .models import Image
    img = Image.objects.create(user=operator_user, file_path="t.jpg", file_format="jpg", timestamp="2025-01-01 10:00")

    # 1. CREATE - Агроном создает диагноз
    api_client.force_authenticate(user=agronomist_user)
    data = {
        'image': img.id,
        'disease': disease.id,
        'confidence': 0.99,
        'is_verified': True
    }
    response = api_client.post('/api/diagnoses/', data)
    assert response.status_code == 201
    assert Diagnosis.objects.count() == 1
    diagnosis_id = response.data['id']

    # 2. READ - Чтение списка диагнозов
    response = api_client.get('/api/diagnoses/')
    assert response.status_code == 200
    assert response.data['count'] == 1

    # 3. READ - Чтение детальной информации
    response = api_client.get(f'/api/diagnoses/{diagnosis_id}/')
    assert response.status_code == 200
    assert response.data['disease'] == disease.id

    # 4. UPDATE - Агроном обновляет диагноз
    response = api_client.patch(f'/api/diagnoses/{diagnosis_id}/', {'confidence': 0.95})
    assert response.status_code == 200
    assert response.data['confidence'] == 0.95

    # 5. Оператор не может создавать диагнозы -> 403
    api_client.force_authenticate(user=operator_user)
    response = api_client.post('/api/diagnoses/', data)
    assert response.status_code == 403

    # 6. DELETE - Админ удаляет диагноз
    api_client.force_authenticate(user=admin_user)
    response = api_client.delete(f'/api/diagnoses/{diagnosis_id}/')
    assert response.status_code == 204
    assert not Diagnosis.objects.filter(id=diagnosis_id).exists()


@pytest.mark.django_db
def test_image_crud_full_cycle(api_client, operator_user, agronomist_user, admin_user, test_section_setup):
    """
    Тест полного CRUD цикла для изображений.
    """
    from .models import Image
    from rest_framework import status

    # 1. CREATE - Оператор загружает изображение (уже протестировано в test_operator_can_upload_image)
    # Создаем изображение напрямую для тестирования других операций
    img = Image.objects.create(
        user=operator_user,
        file_path="test_crud.jpg",
        file_format="jpg",
        section=test_section_setup
    )

    # 2. READ - Оператор читает свое изображение
    api_client.force_authenticate(user=operator_user)
    response = api_client.get(f'/api/images/{img.id}/')
    assert response.status_code == status.HTTP_200_OK
    assert response.data['id'] == img.id

    # 3. READ - Агроном читает все изображения
    api_client.force_authenticate(user=agronomist_user)
    response = api_client.get('/api/images/')
    assert response.status_code == status.HTTP_200_OK
    assert response.data['count'] >= 1

    # 4. UPDATE - Обновление информации об изображении
    response = api_client.patch(f'/api/images/{img.id}/', {'file_format': 'png'})
    assert response.status_code == status.HTTP_200_OK
    img.refresh_from_db()
    assert img.file_format == 'png'

    # 5. DELETE - Удаление изображения
    response = api_client.delete(f'/api/images/{img.id}/')
    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert not Image.objects.filter(id=img.id).exists()