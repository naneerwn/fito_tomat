import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../services/api';
import { ReportData } from '../types/report';
import './DashboardPage.css';

export function DashboardPage() {
  const { data: report, isLoading, error } = useQuery({
    queryKey: ['reports', 'live-summary'],
    queryFn: async () => {
      const response = await api.get('/reports/live-summary/');
      return response.data as ReportData;
    },
  });

  const reportData: ReportData | null = useMemo(() => {
    if (!report) return null;
    return report;
  }, [report]);

  const diagnostics = reportData?.diagnostics ?? { total: 0, avg_confidence: null, distribution: [] };
  const recommendations = reportData?.recommendations ?? { total: 0 };
  const tasks = reportData?.tasks ?? { total: 0, completed_on_time: 0, overdue: 0 };
  const distribution = useMemo(
    () => (Array.isArray(diagnostics.distribution) ? diagnostics.distribution : []),
    [diagnostics.distribution],
  );
  const palette = ['#2563eb', '#22c55e', '#f59e0b', '#ec4899', '#8b5cf6', '#0ea5e9'];
  const pieSum = useMemo(
    () => Math.max(1, distribution.reduce((acc, item) => acc + (item.total || 0), 0)),
    [distribution],
  );
  const maxCount = useMemo(() => {
    if (!distribution.length) return 1;
    return Math.max(...distribution.map((d: any) => d.total || 0), 1);
  }, [distribution]);

  const timeseries = useMemo(
    () => (Array.isArray(reportData?.timeseries) ? reportData.timeseries : []),
    [reportData?.timeseries],
  );

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
          <h3>Распределение выявленных заболеваний</h3>
          <div className="chart-row">
            <div className="pie-chart">
              {distribution.length > 0 ? (
                <svg viewBox="0 0 32 32" className="pie">
                  {distribution.reduce<{ start: number; nodes: JSX.Element[] }>((acc, item, idx) => {
                    const val = item.total || 0;
                    const sweep = (val / pieSum) * 2 * Math.PI;
                    const color = palette[idx % palette.length];
                    const x1 = 16 + 16 * Math.sin(acc.start);
                    const y1 = 16 - 16 * Math.cos(acc.start);
                    const end = acc.start + sweep;
                    const x2 = 16 + 16 * Math.sin(end);
                    const y2 = 16 - 16 * Math.cos(end);
                    const largeArc = sweep > Math.PI ? 1 : 0;
                    const d = `M16,16 L${x1},${y1} A16,16 0 ${largeArc} 1 ${x2},${y2} Z`;
                    acc.nodes.push(
                      <path key={idx} d={d} className="pie-slice" fill={color} />
                    );
                    acc.start = end;
                    return acc;
                  }, { start: 0, nodes: [] }).nodes}
                </svg>
              ) : (
                <p className="no-data">Нет данных</p>
              )}
            </div>
            <div className="disease-list">
              {distribution.length > 0 ? (
                distribution.map((item, idx) => {
                  const width = `${Math.max(8, Math.round((item.total / maxCount) * 100))}%`;
                  const color = palette[idx % palette.length];
                  return (
                    <div key={idx} className="disease-item">
                      <span className="legend-dot" style={{ backgroundColor: color }} />
                      <div className="disease-row">
                        <span className="disease-name">{item.disease__name}</span>
                        <span className="disease-count">{item.total} случаев</span>
                      </div>
                      <div className="disease-bar" style={{ width, backgroundColor: color }} />
                    </div>
                  );
                })
              ) : (
                <p className="no-data">Нет данных о заболеваниях</p>
              )}
            </div>
          </div>
        </div>

        <div className="kpi-card full-width">
          <h3>Динамика заболеваемости по дням</h3>
          {timeseries.length > 0 ? (
            <div className="line-chart-wrapper">
              <svg viewBox="0 0 320 180" className="line-chart">
                <line x1="40" y1="10" x2="40" y2="150" stroke="#cbd5e1" strokeWidth="1" />
                <line x1="40" y1="150" x2="310" y2="150" stroke="#cbd5e1" strokeWidth="1" />
                {timeseries.length > 1 && (
                  <polyline
                    fill="none"
                    stroke="#2563eb"
                    strokeWidth="2"
                    points={timeseries
                      .map((p, idx) => {
                        const x = 40 + (idx / Math.max(1, timeseries.length - 1)) * 260;
                        const maxY = Math.max(...timeseries.map((t) => t.total || 0), 1);
                        const y = 150 - (p.total / maxY) * 120;
                        return `${x},${y}`;
                      })
                      .join(' ')}
                  />
                )}
                {timeseries.map((p, idx) => {
                  const x = 40 + (idx / Math.max(1, timeseries.length - 1)) * 260;
                  const maxY = Math.max(...timeseries.map((t) => t.total || 0), 1);
                  const y = 150 - (p.total / maxY) * 120;
                  return <circle key={idx} cx={x} cy={y} r={3} fill="#2563eb" />;
                })}
                {/** Y labels */}
                {[0, 0.25, 0.5, 0.75, 1].map((t, idx) => {
                  const maxY = Math.max(...timeseries.map((tt) => tt.total || 0), 1);
                  const val = Math.round(maxY * t);
                  const y = 150 - t * 120;
                  return (
                    <g key={idx}>
                      <text x={10} y={y + 4} fontSize="10" fill="#475467">{val}</text>
                      <line x1="38" y1={y} x2="40" y2={y} stroke="#94a3b8" strokeWidth="1" />
                    </g>
                  );
                })}
                {/** X labels */}
                {timeseries.map((p, idx) => {
                  const x = 40 + (idx / Math.max(1, timeseries.length - 1)) * 260;
                  const label = p.date;
                  return (
                    <text key={idx} x={x} y={165} fontSize="9" fill="#475467" textAnchor="middle">
                      {label}
                    </text>
                  );
                })}
              </svg>
            </div>
          ) : (
            <p className="no-data">Нет данных для графика</p>
          )}
        </div>
      </div>
    </section>
  );
}
