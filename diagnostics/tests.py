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
def test_disease_catalog_permissions(api_client, agronomist_user, operator_user):
    """
    Тест: Справочник болезней.
    """
    # 1. Оператор может ЧИТАТЬ список болезней
    Disease.objects.create(name="Rot", description="...", symptoms="...")
    api_client.force_authenticate(user=operator_user)
    response = api_client.get('/api/diseases/')
    assert response.status_code == 200
    assert response.data['count'] == 1

    # 2. Оператор НЕ может СОЗДАВАТЬ болезни -> 403
    # (Тут мы проверяем дефолтные права IsAuthenticated, если мы не ставили IsAdminOrReadOnly,
    # то тест может упасть, и это подскажет нам донастроить views.py!)
    # Допустим, в views.py мы оставили ModelViewSet без явных прав - тогда любой юзер может писать.
    # В ТЗ сказано: "Добавление ... - Агроном, Администратор".
    # Давайте проверим Агронома.

    api_client.force_authenticate(user=agronomist_user)
    data = {'name': 'New Disease', 'description': 'Desc', 'symptoms': 'Symp'}
    response = api_client.post('/api/diseases/', data)
    assert response.status_code == 201


@pytest.mark.django_db
def test_diagnosis_workflow(api_client, agronomist_user, operator_user):
    """
    Тест создания диагноза.
    """
    # Подготовка
    disease = Disease.objects.create(name="X", description="D", symptoms="S")
    # Используем фикстуру для создания картинки, если нужно, или создаем тут
    from .models import Image
    img = Image.objects.create(user=operator_user, file_path="t.jpg", file_format="jpg", timestamp="2025-01-01 10:00")

    # Агроном создает диагноз (по ТЗ диагноз ставит ML или Агроном)
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