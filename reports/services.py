from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, TypedDict, cast

from django.conf import settings
from django.db.models import Avg, Count, F
from django.utils import timezone

from diagnostics.models import Diagnosis
from operations.models import Recommendation, Task
from common.typing import DateTimeLike


class DiseaseDistributionEntry(TypedDict):
    disease__name: str
    total: int


class DiagnosticsPayload(TypedDict):
    total: int
    avg_confidence: float | None
    distribution: List[DiseaseDistributionEntry]


class RecommendationsPayload(TypedDict):
    total: int


class TasksPayload(TypedDict):
    total: int
    completed_on_time: int
    overdue: int


class PeriodPayload(TypedDict):
    start: str
    end: str


class ReportPayload(TypedDict):
    period: PeriodPayload
    diagnostics: DiagnosticsPayload
    recommendations: RecommendationsPayload
    tasks: TasksPayload


def generate_report_payload(
    period_start: DateTimeLike,
    period_end: DateTimeLike,
) -> ReportPayload:
    """
    Aggregate KPI metrics for the requested period.
    """
    current_tz = timezone.get_current_timezone()
    start_dt = cast(datetime, period_start)
    end_dt = cast(datetime, period_end)
    start_dt = timezone.make_aware(start_dt, current_tz) if timezone.is_naive(start_dt) else start_dt
    end_dt = timezone.make_aware(end_dt, current_tz) if timezone.is_naive(end_dt) else end_dt

    diagnoses_qs = Diagnosis.objects.filter(timestamp__range=(start_dt, end_dt))
    tasks_qs = Task.objects.filter(created_at__range=(start_dt, end_dt))
    recommendations_qs = Recommendation.objects.filter(created_at__range=(start_dt, end_dt))

    disease_distribution = list(
        diagnoses_qs.values('disease__name')
        .annotate(total=Count('id'))
        .order_by('-total')
    )
    avg_confidence = diagnoses_qs.aggregate(avg=Avg('confidence'))['avg']

    completed_on_time = tasks_qs.filter(completed_at__isnull=False, completed_at__lte=F('deadline')).count()
    overdue = tasks_qs.filter(deadline__lt=timezone.now(), completed_at__isnull=True).count()

    payload: ReportPayload = {
        'period': {
            'start': start_dt.isoformat(),
            'end': end_dt.isoformat(),
        },
        'diagnostics': {
            'total': diagnoses_qs.count(),
            'avg_confidence': round(avg_confidence, 4) if avg_confidence is not None else None,
            'distribution': disease_distribution,
        },
        'recommendations': {
            'total': recommendations_qs.count(),
        },
        'tasks': {
            'total': tasks_qs.count(),
            'completed_on_time': completed_on_time,
            'overdue': overdue,
        },
    }
    return payload


def persist_report_file(report_id: int, payload: Dict[str, Any]) -> Path:
    file_path = settings.REPORTS_DIR / f'report_{report_id}.json'
    file_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    return file_path

