from django.contrib import admin
from .models import Disease, Treatment, Image, Diagnosis

class TreatmentInline(admin.StackedInline):
    model = Treatment
    extra = 0

@admin.register(Disease)
class DiseaseAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name', 'symptoms')
    inlines = [TreatmentInline] # Можно добавлять лечение прямо в карточке болезни

@admin.register(Image)
class ImageAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'section', 'timestamp', 'uploaded_at')
    list_filter = ('section', 'timestamp')
    readonly_fields = ('uploaded_at',)

@admin.register(Diagnosis)
class DiagnosisAdmin(admin.ModelAdmin):
    # Агроном сразу видит: что за болезнь, уверенность ИИ и проверено ли это
    list_display = ('id', 'image', 'disease', 'confidence', 'is_verified', 'verified_by')
    # Фильтр "Неверифицированные" - критически важен для работы агронома
    list_filter = ('is_verified', 'disease', 'timestamp')
    search_fields = ('disease__name',)
    readonly_fields = ('timestamp',)