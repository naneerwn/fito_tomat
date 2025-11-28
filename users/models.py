from django.db import models
from django.contrib.auth.models import AbstractUser


class Role(models.Model):
    # id создается автоматически (BigAutoField)
    name = models.CharField(max_length=100, verbose_name="Название роли")

    class Meta:
        db_table = 'roles'  # [cite: 801]
        verbose_name = 'Роль'
        verbose_name_plural = 'Роли'

    def __str__(self):
        return self.name


class User(AbstractUser):
    # Стандартные поля Django (username, email, password, is_active, date_joined as created_at) уже есть.
    # Переопределяем или добавляем недостающие согласно ТЗ[cite: 802].

    full_name = models.CharField(max_length=255, verbose_name="Полное имя")
    role = models.ForeignKey(Role, on_delete=models.PROTECT, null=True, blank=True, related_name='users',
                             verbose_name="Роль")

    # Поле created_at в Django обычно называется date_joined, но добавим явное, если нужно строго по ТЗ
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата регистрации")

    class Meta:
        db_table = 'users'  # [cite: 802]
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'