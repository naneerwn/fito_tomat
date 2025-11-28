from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Role, User


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    # Колонки в списке пользователей
    list_display = ('username', 'email', 'full_name', 'role', 'is_active', 'is_staff')
    # Фильтры справа
    list_filter = ('role', 'is_active', 'is_staff')
    # Поля, по которым работает поиск
    search_fields = ('username', 'full_name', 'email')

    # Добавляем наши кастомные поля в форму редактирования
    fieldsets = UserAdmin.fieldsets + (
        ('Дополнительная информация', {'fields': ('full_name', 'role')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Дополнительная информация', {'fields': ('full_name', 'role')}),
    )