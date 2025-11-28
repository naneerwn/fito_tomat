from rest_framework.routers import DefaultRouter
from users.views import UserViewSet, RoleViewSet
from infrastructure.views import GreenhouseViewSet, SectionViewSet
from diagnostics.views import DiseaseViewSet, ImageViewSet, DiagnosisViewSet
from operations.views import RecommendationViewSet, TaskViewSet
from reports.views import ReportViewSet, AuditLogViewSet

router = DefaultRouter()

# Users
router.register(r'users', UserViewSet)
router.register(r'roles', RoleViewSet)

# Infrastructure
router.register(r'greenhouses', GreenhouseViewSet)
router.register(r'sections', SectionViewSet)

# Diagnostics
router.register(r'diseases', DiseaseViewSet)
router.register(r'images', ImageViewSet)
router.register(r'diagnoses', DiagnosisViewSet)

# Operations
router.register(r'recommendations', RecommendationViewSet)
router.register(r'tasks', TaskViewSet)

# Reports & audit
router.register(r'reports', ReportViewSet)
router.register(r'audit-logs', AuditLogViewSet, basename='audit-log')