import { useQuery } from '@tanstack/react-query';
import { api } from '../services/api';
import { ReportData } from '../types/report';
import './DashboardPage.css';

export function DashboardPage() {
  const { data: report, isLoading, error } = useQuery({
    queryKey: ['reports', 'latest'],
    queryFn: async () => {
      const response = await api.get('/reports/');
      return response.data?.results?.[0];
    },
  });

  // Безопасно парсим данные отчёта
  let reportData: ReportData | null = null;
  if (report?.data) {
    try {
      // Если data уже объект, используем его, иначе парсим строку
      reportData = typeof report.data === 'string' ? JSON.parse(report.data) : report.data;
    } catch (e) {
      console.error('Ошибка при парсинге данных отчёта:', e);
      reportData = null;
    }
  }

  if (isLoading) {
    return (
      <section className="dashboard">
        <h1>Дашборд</h1>
        <p>Загрузка данных...</p>
      </section>
    );
  }

  if (error) {
    return (
      <section className="dashboard">
        <h1>Дашборд</h1>
        <div className="empty-state">
          <p>Ошибка при загрузке данных. Попробуйте обновить страницу.</p>
        </div>
      </section>
    );
  }

  if (!reportData) {
    return (
      <section className="dashboard">
        <h1>Дашборд</h1>
        <div className="empty-state">
          <p>Нет данных отчёта. Сгенерируйте новый отчёт на вкладке «Отчёты».</p>
        </div>
      </section>
    );
  }

  const { diagnostics, recommendations, tasks } = reportData;

  return (
    <section className="dashboard">
      <h1>Дашборд</h1>
      <div className="dashboard-grid">
        <div className="kpi-card">
          <h3>Диагностики</h3>
          <div className="kpi-value">{diagnostics.total}</div>
          <div className="kpi-subtitle">
            Средняя точность: {diagnostics.avg_confidence ? `${(diagnostics.avg_confidence * 100).toFixed(1)}%` : 'N/A'}
          </div>
        </div>

        <div className="kpi-card">
          <h3>Рекомендации</h3>
          <div className="kpi-value">{recommendations.total}</div>
          <div className="kpi-subtitle">Всего создано</div>
        </div>

        <div className="kpi-card">
          <h3>Задачи</h3>
          <div className="kpi-value">{tasks.total}</div>
          <div className="kpi-subtitle">
            Выполнено в срок: {tasks.completed_on_time} | Просрочено: {tasks.overdue}
          </div>
        </div>

        <div className="kpi-card full-width">
          <h3>Распределение заболеваний</h3>
          <div className="disease-list">
            {diagnostics.distribution.length > 0 ? (
              diagnostics.distribution.map((item, idx) => (
                <div key={idx} className="disease-item">
                  <span className="disease-name">{item.disease__name}</span>
                  <span className="disease-count">{item.total} случаев</span>
                </div>
              ))
            ) : (
              <p className="no-data">Нет данных о заболеваниях</p>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
