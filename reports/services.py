from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from django.conf import settings
from django.db.models import Avg, Count, F
from django.utils import timezone

from diagnostics.models import Diagnosis
from operations.models import Recommendation, Task


def generate_report_payload(period_start, period_end) -> Dict[str, Any]:
    """
    Aggregate KPI metrics for the requested period.
    """
    current_tz = timezone.get_current_timezone()
    period_start = timezone.make_aware(period_start, current_tz) if timezone.is_naive(period_start) else period_start
    period_end = timezone.make_aware(period_end, current_tz) if timezone.is_naive(period_end) else period_end

    diagnoses_qs = Diagnosis.objects.filter(timestamp__range=(period_start, period_end))
    tasks_qs = Task.objects.filter(created_at__range=(period_start, period_end))
    recommendations_qs = Recommendation.objects.filter(created_at__range=(period_start, period_end))

    disease_distribution = list(
        diagnoses_qs.values('disease__name')
        .annotate(total=Count('id'))
        .order_by('-total')
    )
    avg_confidence = diagnoses_qs.aggregate(avg=Avg('confidence'))['avg']

    completed_on_time = tasks_qs.filter(completed_at__isnull=False, completed_at__lte=F('deadline')).count()
    overdue = tasks_qs.filter(deadline__lt=timezone.now(), completed_at__isnull=True).count()

    payload: Dict[str, Any] = {
        'period': {
            'start': period_start.isoformat(),
            'end': period_end.isoformat(),
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

