from django.contrib import admin
from .models import Recommendation, Task

class TaskInline(admin.TabularInline):
    model = Task
    extra = 0

@admin.register(Recommendation)
class RecommendationAdmin(admin.ModelAdmin):
    list_display = ('id', 'diagnosis', 'agronomist', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    inlines = [TaskInline] # Видно задачи внутри рекомендации

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('id', 'description', 'operator', 'status', 'deadline')
    list_filter = ('status', 'operator', 'deadline')
    search_fields = ('description',)