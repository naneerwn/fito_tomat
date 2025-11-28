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

  const { data: tasks, isLoading } = useQuery({
    queryKey: ['tasks', filter],
    queryFn: async () => {
      const response = await api.get('/tasks/');
      let results = response.data.results as Task[];
      
      if (filter === 'my' && user) {
        results = results.filter(t => t.operator === user.id);
      } else if (filter === 'pending') {
        results = results.filter(t => t.status !== 'Выполнена' && (!t.completed_at || new Date(t.completed_at) > new Date(t.deadline)));
      } else if (filter === 'completed') {
        results = results.filter(t => t.status === 'Выполнена');
      }
      
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

  const completeTaskMutation = useMutation({
    mutationFn: async (id: number) => {
      return api.patch(`/tasks/${id}/`, {
        status: 'Выполнена',
        completed_at: new Date().toISOString(),
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
    },
  });

  const handleStatusChange = (taskId: number, newStatus: string) => {
    updateStatusMutation.mutate({ id: taskId, status: newStatus });
  };

  const handleComplete = (taskId: number) => {
    completeTaskMutation.mutate(taskId);
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'Выполнена':
        return '#10b981';
      case 'В работе':
        return '#f59e0b';
      case 'Назначена':
        return '#3b82f6';
      default:
        return '#64748b';
    }
  };

  const isOverdue = (task: Task) => {
    if (task.completed_at) return false;
    return new Date(task.deadline) < new Date();
  };

  if (isLoading) {
    return <div className="tasks-page">Загрузка...</div>;
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
            Выполненные
          </button>
        </div>
      </div>

      {tasks && tasks.length > 0 ? (
        <div className="tasks-list">
          {tasks.map((task) => (
            <div
              key={task.id}
              className={`task-card ${isOverdue(task) ? 'overdue' : ''} ${task.status === 'Выполнена' ? 'completed' : ''}`}
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
                {task.description}
              </div>

              <div className="task-meta">
                <div className="task-date">
                  <strong>Срок:</strong> {new Date(task.deadline).toLocaleDateString('ru-RU')}
                  {isOverdue(task) && <span className="overdue-badge">Просрочено</span>}
                </div>
                {task.completed_at && (
                  <div className="task-date">
                    <strong>Выполнено:</strong> {new Date(task.completed_at).toLocaleString('ru-RU')}
                  </div>
                )}
              </div>

              {task.status !== 'Выполнена' && user?.role?.name === 'Оператор' && (
                <div className="task-actions">
                  <select
                    value={task.status}
                    onChange={(e) => handleStatusChange(task.id, e.target.value)}
                    className="status-select"
                  >
                    <option value="Назначена">Назначена</option>
                    <option value="В работе">В работе</option>
                    <option value="Выполнена">Выполнена</option>
                  </select>
                  <button
                    className="btn-complete"
                    onClick={() => handleComplete(task.id)}
                    disabled={completeTaskMutation.isPending}
                  >
                    {completeTaskMutation.isPending ? 'Выполнение...' : 'Отметить выполненной'}
                  </button>
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
