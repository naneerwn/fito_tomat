import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../services/api';
import { Report } from '../types/report';
import './ReportsPage.css';

export function ReportsPage() {
  const queryClient = useQueryClient();
  const [showGenerateForm, setShowGenerateForm] = useState(false);
  const [downloadFormatById, setDownloadFormatById] = useState<Record<number, 'excel' | 'pdf'>>({});

  const { data: reports, isLoading } = useQuery({
    queryKey: ['reports'],
    queryFn: async () => {
      const response = await api.get('/reports/');
      return response.data.results as Report[];
    },
  });

  const generateReportMutation = useMutation({
    mutationFn: async (data: { report_type: string; period_start: string; period_end: string }) => {
      return api.post('/reports/', data);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['reports'] });
      setShowGenerateForm(false);
    },
  });

  const handleGenerate = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    generateReportMutation.mutate({
      report_type: formData.get('report_type') as string,
      period_start: formData.get('period_start') as string,
      period_end: formData.get('period_end') as string,
    });
  };

  const getFormat = (reportId: number) => downloadFormatById[reportId] || 'excel';

  const handleDownload = async (reportId: number) => {
    try {
      const format = getFormat(reportId);
      const endpoint = format === 'excel' ? `/reports/${reportId}/download-excel/` : `/reports/${reportId}/download-pdf/`;

      const filename = format === 'excel' ? `report_${reportId}.xlsx` : `report_${reportId}.pdf`;

      const response = await api.get(endpoint, {
        responseType: 'blob',
      });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Ошибка при скачивании файла:', error);
      alert('Не удалось скачать файл. Попробуйте позже.');
    }
  };

  if (isLoading) {
    return <div className="reports-page">Загрузка...</div>;
  }

  return (
    <div className="reports-page">
      <div className="reports-header">
        <h1>Отчёты</h1>
        <button
          className="btn-generate"
          onClick={() => setShowGenerateForm(!showGenerateForm)}
        >
          {showGenerateForm ? 'Отмена' : '+ Сгенерировать отчёт'}
        </button>
      </div>

      {showGenerateForm && (
        <div className="generate-form-container">
          <h2>Генерация нового отчёта</h2>
          <form onSubmit={handleGenerate} className="generate-form">
            <div className="form-group">
              <label>
                Тип отчёта:
                <select name="report_type" required>
                  <option value="diagnostics_summary">Сводка по диагностике</option>
                  <option value="tasks_summary">Сводка по задачам</option>
                  <option value="full_report">Полный отчёт</option>
                </select>
              </label>
            </div>
            <div className="form-group">
              <label>
                Начало периода:
                <input
                  type="datetime-local"
                  name="period_start"
                  required
                  defaultValue={new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString().slice(0, 16)}
                />
              </label>
            </div>
            <div className="form-group">
              <label>
                Конец периода:
                <input
                  type="datetime-local"
                  name="period_end"
                  required
                  defaultValue={new Date().toISOString().slice(0, 16)}
                />
              </label>
            </div>
            <button
              type="submit"
              className="btn-submit"
              disabled={generateReportMutation.isPending}
            >
              {generateReportMutation.isPending ? 'Генерация...' : 'Сгенерировать'}
            </button>
          </form>
        </div>
      )}

      <div className="reports-list">
        {reports && reports.length > 0 ? (
          reports.map((report) => {
            const reportData = typeof report.data === 'string' ? JSON.parse(report.data) : report.data;
            return (
              <div key={report.id} className="report-card">
                <div className="report-header">
                  <div>
                    <h3>Отчёт #{report.id}</h3>
                    <p className="report-meta">
                      {report.report_type} • {new Date(report.generated_at).toLocaleString('ru-RU')}
                    </p>
                  </div>
                  <div className="download-controls">
                    <select
                      value={getFormat(report.id)}
                      onChange={(e) =>
                        setDownloadFormatById((prev) => ({
                          ...prev,
                          [report.id]: e.target.value as 'excel' | 'pdf',
                        }))
                      }
                    >
                      <option value="excel">Excel (XLSX)</option>
                      <option value="pdf">PDF</option>
                    </select>
                    <button
                      className="btn-download"
                      onClick={() => handleDownload(report.id)}
                    >
                      Скачать
                    </button>
                  </div>
                </div>
                <div className="report-period">
                  <strong>Период:</strong> {new Date(report.period_start).toLocaleDateString('ru-RU')} - {new Date(report.period_end).toLocaleDateString('ru-RU')}
                </div>
                {reportData && (
                  <div className="report-summary">
                    <div className="summary-item">
                      <span className="summary-label">Диагностики:</span>
                      <span className="summary-value">{reportData.diagnostics?.total || 0}</span>
                    </div>
                    <div className="summary-item">
                      <span className="summary-label">Рекомендации:</span>
                      <span className="summary-value">{reportData.recommendations?.total || 0}</span>
                    </div>
                    <div className="summary-item">
                      <span className="summary-label">Задачи:</span>
                      <span className="summary-value">{reportData.tasks?.total || 0}</span>
                    </div>
                  </div>
                )}
              </div>
            );
          })
        ) : (
          <div className="empty-state">
            <p>Нет сгенерированных отчётов</p>
          </div>
        )}
      </div>
    </div>
  );
}
