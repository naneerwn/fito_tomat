import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../services/api';
import { Diagnosis, Disease } from '../types/diagnosis';
import './DiagnosesPage.css';

export function DiagnosesPage() {
  const queryClient = useQueryClient();
  const [selectedDiagnosis, setSelectedDiagnosis] = useState<Diagnosis | null>(null);
  const [showRecommendationForm, setShowRecommendationForm] = useState(false);

  const { data: diagnoses, isLoading } = useQuery({
    queryKey: ['diagnoses'],
    queryFn: async () => {
      const response = await api.get('/diagnoses/');
      return response.data.results as Diagnosis[];
    },
  });

  const { data: diseases } = useQuery({
    queryKey: ['diseases'],
    queryFn: async () => {
      const response = await api.get('/diseases/');
      return response.data.results as Disease[];
    },
  });

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
    mutationFn: async (data: { diagnosis: number; treatment_plan_text: string; status: string }) => {
      return api.post('/recommendations/', data);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['recommendations'] });
      setShowRecommendationForm(false);
      setSelectedDiagnosis(null);
    },
  });

  const handleVerify = (diagnosis: Diagnosis) => {
    if (diagnosis.disease) {
      verifyMutation.mutate({ id: diagnosis.id, diseaseId: diagnosis.disease });
    }
  };

  const handleCreateRecommendation = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    if (selectedDiagnosis) {
      createRecommendationMutation.mutate({
        diagnosis: selectedDiagnosis.id,
        treatment_plan_text: formData.get('treatment_plan') as string,
        status: 'New',
      });
    }
  };

  if (isLoading) {
    return <div className="diagnoses-page">Загрузка...</div>;
  }

  return (
    <div className="diagnoses-page">
      <h1>Диагностика заболеваний</h1>

      <div className="diagnoses-layout">
        <div className="diagnoses-list">
          <h2>Очередь диагнозов</h2>
          {diagnoses && diagnoses.length > 0 ? (
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
                    <p><strong>Заболевание:</strong> {diag.disease_name || `ID: ${diag.disease}`}</p>
                    <p><strong>Уверенность:</strong> {(diag.confidence * 100).toFixed(1)}%</p>
                    <p><strong>Дата:</strong> {new Date(diag.timestamp).toLocaleString('ru-RU')}</p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="empty-message">Нет диагнозов для проверки</p>
          )}
        </div>

        {selectedDiagnosis && (
          <div className="diagnosis-detail">
            <h2>Детали диагноза #{selectedDiagnosis.id}</h2>
            
            {/* Визуализация изображений */}
            <div className="detail-section">
              <h3>Визуализация</h3>
              <div className="image-comparison">
                {selectedDiagnosis.heatmap_url ? (
                  <>
                    <div className="image-container">
                      <img
                        src={selectedDiagnosis.heatmap_url}
                        alt="Тепловая карта"
                        className="diagnosis-image"
                      />
                      <p className="image-label">Тепловая карта (GRAD-CAM)</p>
                      <p className="image-note">Красные зоны указывают на области поражения</p>
                    </div>
                  </>
                ) : (
                  <p className="no-heatmap">Тепловая карта ещё не сгенерирована</p>
                )}
              </div>
            </div>

            <div className="detail-section">
              <h3>Информация</h3>
              <p><strong>Заболевание:</strong> {selectedDiagnosis.disease_name || `ID: ${selectedDiagnosis.disease}`}</p>
              <p><strong>Уверенность модели:</strong> {(selectedDiagnosis.confidence * 100).toFixed(1)}%</p>
              <p><strong>Статус:</strong> {selectedDiagnosis.is_verified ? 'Подтверждён' : 'Ожидает проверки'}</p>
            </div>

            {!selectedDiagnosis.is_verified && (
              <div className="detail-section">
                <h3>Действия</h3>
                <button
                  className="btn btn-primary"
                  onClick={() => handleVerify(selectedDiagnosis)}
                  disabled={verifyMutation.isPending}
                >
                  {verifyMutation.isPending ? 'Подтверждение...' : 'Подтвердить диагноз'}
                </button>
                <button
                  className="btn btn-secondary"
                  onClick={() => setShowRecommendationForm(true)}
                >
                  Создать рекомендацию
                </button>
              </div>
            )}

            {showRecommendationForm && (
              <div className="detail-section">
                <h3>Создание рекомендации</h3>
                <form onSubmit={handleCreateRecommendation}>
                  <label>
                    План лечения:
                    <textarea
                      name="treatment_plan"
                      rows={6}
                      required
                      placeholder="Опишите план лечения..."
                    />
                  </label>
                  <div className="form-actions">
                    <button type="submit" className="btn btn-primary" disabled={createRecommendationMutation.isPending}>
                      {createRecommendationMutation.isPending ? 'Создание...' : 'Создать рекомендацию'}
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
        )}
      </div>
    </div>
  );
}

