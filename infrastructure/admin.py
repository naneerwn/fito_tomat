from django.contrib import admin
from .models import Greenhouse, Section

# Позволяет добавлять секции прямо внутри страницы теплицы
class SectionInline(admin.TabularInline):
    model = Section
    extra = 1

@admin.register(Greenhouse)
class GreenhouseAdmin(admin.ModelAdmin):
    list_display = ('name', 'location')
    search_fields = ('name', 'location')
    inlines = [SectionInline]

@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ('name', 'greenhouse', 'description')
    list_filter = ('greenhouse',) # Удобный фильтр по теплицам
    search_fields = ('name',)