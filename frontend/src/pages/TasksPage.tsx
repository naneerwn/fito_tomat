import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../services/api';
import { useAuth } from '../hooks/useAuth';
import { Task } from '../types/task';
import './TasksPage.css';

export function TasksPage() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [filter, setFilter] = useState<'all' | 'my' | 'pending' | 'completed'>('my');

  const { data: tasks, isLoading, error } = useQuery({
    queryKey: ['tasks', filter],
    queryFn: async () => {
      const response = await api.get('/tasks/');
      let results = (response.data.results || []) as Task[];
      
      // Фильтрация на клиенте (бэкенд уже фильтрует для операторов)
      if (filter === 'my' && user) {
        results = results.filter(t => t.operator === user.id);
      } else if (filter === 'pending') {
        results = results.filter(t => t.status === 'В работе');
      } else if (filter === 'completed') {
        results = results.filter(t => t.status === 'Закрыта');
      }
      // filter === 'all' - показываем все задачи без дополнительной фильтрации
      
      return results;
    },
  });

  const updateStatusMutation = useMutation({
    mutationFn: async ({ id, status }: { id: number; status: string }) => {
      return api.patch(`/tasks/${id}/`, { status });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
    },
  });

  const handleStatusChange = (taskId: number, newStatus: string) => {
    updateStatusMutation.mutate({ id: taskId, status: newStatus });
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'Закрыта':
        return '#10b981';
      case 'В работе':
        return '#f59e0b';
      case 'Назначена':
        return '#3b82f6';
      default:
        return '#64748b';
    }
  };
  
  const canChangeStatus = (status: string) => {
    // Нельзя изменять задачу со статусом "Закрыта"
    return status !== 'Закрыта';
  };

  const isOverdue = (task: Task) => {
    if (task.completed_at) return false;
    return new Date(task.deadline) < new Date();
  };

  if (isLoading) {
    return <div className="tasks-page">Загрузка...</div>;
  }

  if (error) {
    return <div className="tasks-page">Ошибка загрузки задач: {String(error)}</div>;
  }

  return (
    <div className="tasks-page">
      <div className="tasks-header">
        <h1>Задачи</h1>
        <div className="filter-tabs">
          <button
            className={filter === 'my' ? 'active' : ''}
            onClick={() => setFilter('my')}
          >
            Мои задачи
          </button>
          <button
            className={filter === 'all' ? 'active' : ''}
            onClick={() => setFilter('all')}
          >
            Все задачи
          </button>
          <button
            className={filter === 'pending' ? 'active' : ''}
            onClick={() => setFilter('pending')}
          >
            В работе
          </button>
          <button
            className={filter === 'completed' ? 'active' : ''}
            onClick={() => setFilter('completed')}
          >
            Закрытые
          </button>
        </div>
      </div>

      {tasks && tasks.length > 0 ? (
        <div className="tasks-list">
          {tasks.map((task) => (
            <div
              key={task.id}
              className={`task-card ${isOverdue(task) ? 'overdue' : ''} ${task.status === 'Закрыта' ? 'completed' : ''}`}
            >
              <div className="task-header">
                <div className="task-id">Задача #{task.id}</div>
                <div
                  className="task-status"
                  style={{ backgroundColor: getStatusColor(task.status) }}
                >
                  {task.status}
                </div>
              </div>
              
              <div className="task-description">
                <strong>Описание:</strong> {task.description}
              </div>

              {task.treatment_plan && (
                <div className="task-treatment-plan" style={{ marginTop: '10px', padding: '10px', backgroundColor: '#f3f4f6', borderRadius: '4px' }}>
                  <strong>План лечения:</strong>
                  <div style={{ marginTop: '5px' }}>{task.treatment_plan}</div>
                </div>
              )}

              <div className="task-meta">
                <div className="task-date">
                  <strong>Срок:</strong> {new Date(task.deadline).toLocaleDateString('ru-RU')}
                  {isOverdue(task) && <span className="overdue-badge">Просрочено</span>}
                </div>
                {task.completed_at && (
                  <div className="task-date">
                    <strong>Закрыто:</strong> {new Date(task.completed_at).toLocaleString('ru-RU')}
                  </div>
                )}
              </div>

              {canChangeStatus(task.status) && (
                <div className="task-actions">
                  <label htmlFor={`status-select-${task.id}`} style={{ marginRight: '10px' }}>
                    <strong>Статус:</strong>
                  </label>
                  <select
                    id={`status-select-${task.id}`}
                    value={task.status}
                    onChange={(e) => handleStatusChange(task.id, e.target.value)}
                    className="status-select"
                    disabled={updateStatusMutation.isPending}
                  >
                    <option value="Назначена">Назначена</option>
                    <option value="В работе">В работе</option>
                    <option value="Закрыта">Закрыта</option>
                  </select>
                  {updateStatusMutation.isPending && (
                    <span style={{ marginLeft: '10px', color: '#666' }}>Сохранение...</span>
                  )}
                </div>
              )}
              
              {!canChangeStatus(task.status) && (
                <div className="task-actions" style={{ color: '#666', fontStyle: 'italic', padding: '10px' }}>
                  Задача закрыта и не может быть изменена
                </div>
              )}
            </div>
          ))}
        </div>
      ) : (
        <div className="empty-state">
          <p>Нет задач для отображения</p>
        </div>
      )}
    </div>
  );
}
