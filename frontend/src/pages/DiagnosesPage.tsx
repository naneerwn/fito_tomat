import { FormEvent, useEffect, useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../services/api';
import { Diagnosis, Disease } from '../types/diagnosis';
import { AuthUser } from '../types/user';
import './DiagnosesPage.css';

export function DiagnosesPage() {
  const queryClient = useQueryClient();
  const [selectedDiagnosis, setSelectedDiagnosis] = useState<Diagnosis | null>(null);
  const [showRecommendationForm, setShowRecommendationForm] = useState(false);
  const [selectedDiseaseId, setSelectedDiseaseId] = useState<number | null>(null);
  const [treatmentPlan, setTreatmentPlan] = useState<string>('');
  const [selectedOperatorId, setSelectedOperatorId] = useState<number | null>(null);
  const [deadline, setDeadline] = useState<string>('');
  const [showRecreateForm, setShowRecreateForm] = useState(false);
  const [selectedModelForRecreate, setSelectedModelForRecreate] = useState<string>('');

  const [page, setPage] = useState<number>(1);
  const [totalCount, setTotalCount] = useState<number>(0);
  const pageSize = 10;
  const totalPages = Math.max(1, Math.ceil(totalCount / pageSize) || 1);

  const { data: diagnoses, isLoading, isFetching } = useQuery({
    queryKey: ['diagnoses', page],
    queryFn: async () => {
      const response = await api.get('/diagnoses/', {
        params: {
          page,
          ordering: '-timestamp',
        },
      });
      setTotalCount(response.data.count ?? 0);
      return response.data.results as Diagnosis[];
    },
    keepPreviousData: true,
  });

  const { data: diseases } = useQuery({
    queryKey: ['diseases'],
    queryFn: async () => {
      const response = await api.get('/diseases/');
      return response.data.results as Disease[];
    },
  });

  const { data: users } = useQuery({
    queryKey: ['users'],
    queryFn: async () => {
      const response = await api.get('/users/');
      return response.data.results as AuthUser[];
    },
  });

  const { data: availableModels = [] } = useQuery({
    queryKey: ['available-models'],
    queryFn: async () => {
      const { data } = await api.get('/images/available-models/');
      return data.models || [];
    },
  });

  const operators = users?.filter((u) => u.role_name === 'Оператор') ?? [];

  const verifyMutation = useMutation({
    mutationFn: async ({ id, diseaseId }: { id: number; diseaseId: number }) => {
      return api.patch(`/diagnoses/${id}/`, {
        disease: diseaseId,
        is_verified: true,
        verified_at: new Date().toISOString(),
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['diagnoses'] });
      setSelectedDiagnosis(null);
    },
  });

  const createRecommendationMutation = useMutation({
    mutationFn: async (data: {
      diagnosis: number;
      treatment_plan_text: string;
      status: string;
      operator_id: number;
      deadline: string;
      task_description?: string;
    }) => {
      return api.post('/recommendations/', data);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['recommendations'] });
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      setShowRecommendationForm(false);
      setSelectedDiagnosis(null);
      setTreatmentPlan('');
      setSelectedOperatorId(null);
      setDeadline('');
    },
  });

  const recreateDiagnosisMutation = useMutation({
    mutationFn: async ({ diagnosisId, modelType }: { diagnosisId: number; modelType: string }) => {
      const { data } = await api.post(`/diagnoses/${diagnosisId}/recreate/`, { model_type: modelType });
      return data as Diagnosis;
    },
    onSuccess: (newDiagnosis) => {
      // Обновляем список диагнозов и устанавливаем выбранным новый диагноз
      queryClient.invalidateQueries({ queryKey: ['diagnoses'] });
      setShowRecreateForm(false);
      setSelectedModelForRecreate('');
      setSelectedDiagnosis(newDiagnosis);
    },
  });


  const handleCreateRecommendation = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!selectedDiagnosis || !selectedOperatorId || !deadline || !treatmentPlan.trim()) {
      return;
    }

    const diseaseId = selectedDiseaseId ?? selectedDiagnosis.disease;

    // Подтверждаем диагноз с исправленной болезнью (если ещё не подтверждён)
    // Подтверждение возможно ТОЛЬКО при создании рекомендации
    if (!selectedDiagnosis.is_verified && diseaseId) {
      await verifyMutation.mutateAsync({ id: selectedDiagnosis.id, diseaseId });
    }

    await createRecommendationMutation.mutateAsync({
      diagnosis: selectedDiagnosis.id,
      treatment_plan_text: treatmentPlan,
      status: 'Новая',
      operator_id: selectedOperatorId,
      deadline,
      task_description: `Выполнить план лечения по диагнозу #${selectedDiagnosis.id}`,
    });
  };

  // Обновляем черновик рекомендации при изменении диагноза или выборе нового
  useEffect(() => {
    if (selectedDiagnosis) {
      setSelectedDiseaseId(selectedDiagnosis.disease);
      updateTreatmentPlanDraft(selectedDiagnosis.disease);
      setSelectedOperatorId(null);
      setDeadline('');
    } else {
      setSelectedDiseaseId(null);
      setTreatmentPlan('');
      setSelectedOperatorId(null);
      setDeadline('');
    }
  }, [selectedDiagnosis]);

  // Обновляем черновик рекомендации при изменении выбранного заболевания
  useEffect(() => {
    if (selectedDiseaseId && diseases) {
      updateTreatmentPlanDraft(selectedDiseaseId);
    }
  }, [selectedDiseaseId, diseases]);

  const updateTreatmentPlanDraft = (diseaseId: number) => {
    const disease = diseases?.find((d) => d.id === diseaseId);
    const diseaseName = disease?.name || '';
    setTreatmentPlan(
      diseaseName
        ? `Рекомендация по лечению заболевания "${diseaseName}". Уточните препараты, дозировки и график обработок согласно внутренним регламентам.`
        : 'Опишите план лечения: препараты, дозировки, кратность и меры предосторожности.',
    );
  };

  if (isLoading) {
    return <div className="diagnoses-page">Загрузка...</div>;
  }

  return (
    <div className="diagnoses-page">
      <h1>Диагностика заболеваний</h1>
      <div className="diagnoses-toolbar">
        <div>
          <h2>Очередь диагнозов</h2>
          <p className="toolbar-hint">Выберите запись, чтобы открыть детали и действия</p>
        </div>
        <div className="pagination">
          <button
            className="btn btn-secondary"
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1 || isFetching}
          >
            ⟵ Пред
          </button>
          <span className="pagination-info">
            Стр. {page} из {totalPages}
          </span>
          <button
            className="btn btn-secondary"
            onClick={() => setPage((p) => (p < totalPages ? p + 1 : p))}
            disabled={page >= totalPages || isFetching}
          >
            След ⟶
          </button>
        </div>
      </div>

      <div className={`diagnoses-layout ${selectedDiagnosis ? 'with-detail' : ''}`}>
        <div className="diagnoses-list">
          {isLoading || isFetching ? (
            <p className="empty-message">Загрузка...</p>
          ) : diagnoses && diagnoses.length > 0 ? (
            <div className="diagnosis-cards">
              {diagnoses.map((diag) => (
                <div
                  key={diag.id}
                  className={`diagnosis-card ${selectedDiagnosis?.id === diag.id ? 'selected' : ''} ${diag.is_verified ? 'verified' : ''}`}
                  onClick={() => setSelectedDiagnosis(diag)}
                >
                  <div className="diagnosis-header">
                    <span className="diagnosis-id">#{diag.id}</span>
                    {diag.is_verified && <span className="badge verified-badge">Подтверждён</span>}
                    {!diag.is_verified && <span className="badge pending-badge">Ожидает проверки</span>}
                  </div>
                  <div className="diagnosis-info">
                    <p>
                      <strong>Заболевание:</strong> {diag.disease_name || `ID: ${diag.disease}`}
                      {diag.is_manually_changed && (
                        <span className="badge changed-badge" title={`Исправлено с "${diag.ml_disease_name || 'ML диагноз'}"`}>
                          Исправлено
                        </span>
                      )}
                    </p>
                    <p>
                      <strong>Уверенность:</strong> {(diag.confidence * 100).toFixed(1)}%
                    </p>
                    <p><strong>Дата:</strong> {new Date(diag.timestamp).toLocaleString('ru-RU')}</p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="empty-message">Нет диагнозов для проверки</p>
          )}
        </div>

        {selectedDiagnosis ? (
          <div className="diagnosis-detail">
            <div className="diagnosis-detail-header">
              <h2>Детали диагноза #{selectedDiagnosis.id}</h2>
              <button
                className="btn-close"
                onClick={() => {
                  setSelectedDiagnosis(null);
                  setShowRecommendationForm(false);
                }}
                aria-label="Закрыть детали"
              >
                ✕
              </button>
            </div>
            
            {/* Визуализация изображений */}
            <div className="detail-section">
              <h3>Визуализация</h3>
              <div className="image-comparison">
                {selectedDiagnosis.image_url && (
                  <div className="image-container">
                    <img
                      src={selectedDiagnosis.image_url}
                      alt="Оригинальное изображение"
                      className="diagnosis-image"
                    />
                    <p className="image-label">Оригинальное изображение</p>
                  </div>
                )}
                {selectedDiagnosis.heatmap_url ? (
                  <div className="image-container">
                    <img
                      src={selectedDiagnosis.heatmap_url}
                      alt="Тепловая карта"
                      className="diagnosis-image"
                    />
                    <p className="image-label">Тепловая карта (GRAD-CAM)</p>
                    <p className="image-note">Красные зоны указывают на области поражения</p>
                  </div>
                ) : (
                  <p className="no-heatmap">Тепловая карта ещё не сгенерирована</p>
                )}
              </div>
            </div>

              <div className="detail-section">
                <h3>Информация</h3>
                <label className="field-label">
                  <span>Диагноз (можно исправить):</span>
                  <select
                    value={selectedDiseaseId ?? selectedDiagnosis.disease}
                    onChange={(e) => setSelectedDiseaseId(Number(e.target.value))}
                    disabled={selectedDiagnosis.is_verified}
                  >
                    {diseases?.map((d) => (
                      <option key={d.id} value={d.id}>
                        {d.name}
                      </option>
                    ))}
                  </select>
                  {selectedDiagnosis.is_manually_changed && selectedDiagnosis.ml_disease_name && (
                    <p className="disease-change-note">
                      <small>
                        ⚠️ Изменено с "{selectedDiagnosis.ml_disease_name}" (ML диагноз)
                      </small>
                    </p>
                  )}
                </label>
                <p>
                  <strong>Уверенность модели:</strong> {(selectedDiagnosis.confidence * 100).toFixed(1)}%
                </p>
                {selectedDiagnosis.model_type_display && (
                  <p><strong>Модель:</strong> {selectedDiagnosis.model_type_display}</p>
                )}
                <p><strong>Статус:</strong> {selectedDiagnosis.is_verified ? 'Подтверждён' : 'Ожидает проверки и создания рекомендации'}</p>
              </div>

            {!selectedDiagnosis.is_verified && (
              <div className="detail-section">
                <h3>Действия</h3>
                <p className="action-note">
                  <small>Для подтверждения диагноза необходимо создать рекомендацию и задачу.</small>
                </p>
                <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                  <button
                    className="btn btn-primary"
                    onClick={() => setShowRecommendationForm(true)}
                  >
                    Создать рекомендацию и задачу
                  </button>
                  <button
                    className="btn btn-secondary"
                    onClick={() => setShowRecreateForm(true)}
                  >
                    Пересоздать с другой моделью
                  </button>
                </div>
              </div>
            )}

            {showRecreateForm && (
              <div className="detail-section">
                <h3>Пересоздать диагноз с другой моделью</h3>
                <p className="action-note">
                  <small>Выберите ML-модель для пересоздания диагноза. Старый диагноз будет удален.</small>
                </p>
                <label>
                  ML-модель:
                  <select
                    value={selectedModelForRecreate}
                    onChange={(e) => setSelectedModelForRecreate(e.target.value)}
                    required
                  >
                    <option value="">Выберите модель</option>
                    {availableModels.map((model: any) => (
                      <option key={model.value} value={model.value} title={model.description}>
                        {model.label}
                      </option>
                    ))}
                  </select>
                </label>
                <div className="form-actions">
                  <button
                    type="button"
                    className="btn btn-primary"
                    onClick={() => {
                      if (selectedModelForRecreate && selectedDiagnosis) {
                        recreateDiagnosisMutation.mutate({
                          diagnosisId: selectedDiagnosis.id,
                          modelType: selectedModelForRecreate,
                        });
                      }
                    }}
                    disabled={!selectedModelForRecreate || recreateDiagnosisMutation.isPending}
                  >
                    {recreateDiagnosisMutation.isPending ? 'Пересоздание...' : 'Пересоздать диагноз'}
                  </button>
                  <button
                    type="button"
                    className="btn btn-secondary"
                    onClick={() => {
                      setShowRecreateForm(false);
                      setSelectedModelForRecreate('');
                    }}
                  >
                    Отмена
                  </button>
                </div>
              </div>
            )}

            {showRecommendationForm && (
              <div className="detail-section">
                <h3>Создание рекомендации и задачи</h3>
                <form onSubmit={handleCreateRecommendation}>
                  <label>
                    План лечения:
                    <textarea
                      name="treatment_plan"
                      rows={6}
                      required
                      placeholder="Опишите план лечения..."
                      value={treatmentPlan}
                      onChange={(e) => setTreatmentPlan(e.target.value)}
                    />
                  </label>
                  <label>
                    Оператор для выполнения:
                    <select
                      required
                      value={selectedOperatorId ?? ''}
                      onChange={(e) => setSelectedOperatorId(Number(e.target.value))}
                    >
                      <option value="">Выберите оператора</option>
                      {operators.map((op) => (
                        <option key={op.id} value={op.id}>
                          {op.full_name || op.username}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    Срок выполнения задачи:
                    <input
                      type="datetime-local"
                      required
                      value={deadline}
                      onChange={(e) => setDeadline(e.target.value)}
                    />
                  </label>
                  <div className="form-actions">
                    <button
                      type="submit"
                      className="btn btn-primary"
                      disabled={createRecommendationMutation.isPending || verifyMutation.isPending}
                    >
                      {createRecommendationMutation.isPending || verifyMutation.isPending
                        ? 'Сохранение...'
                        : 'Создать рекомендацию и задачу'}
                    </button>
                    <button
                      type="button"
                      className="btn btn-secondary"
                      onClick={() => setShowRecommendationForm(false)}
                    >
                      Отмена
                    </button>
                  </div>
                </form>
              </div>
            )}
          </div>
        ) : (
          <div className="diagnosis-detail-placeholder">
            <p>Выберите диагноз из списка для просмотра деталей</p>
          </div>
        )}
      </div>
    </div>
  );
}

