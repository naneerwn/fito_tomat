import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../services/api';
import { AuthUser } from '../types/user';
import './AdminPage.css';

export function AdminPage() {
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<'users' | 'roles' | 'audit'>('users');
  const [showUserForm, setShowUserForm] = useState(false);
  const [editingUser, setEditingUser] = useState<AuthUser | null>(null);

  const { data: users } = useQuery({
    queryKey: ['users'],
    queryFn: async () => {
      const response = await api.get('/users/');
      return response.data.results as AuthUser[];
    },
  });

  const { data: roles } = useQuery({
    queryKey: ['roles'],
    queryFn: async () => {
      const response = await api.get('/roles/');
      return response.data.results;
    },
  });

  const { data: auditLogs } = useQuery({
    queryKey: ['audit-logs'],
    queryFn: async () => {
      const response = await api.get('/audit-logs/');
      return response.data.results;
    },
    enabled: activeTab === 'audit',
  });

  const createUserMutation = useMutation({
    mutationFn: async (data: { username: string; password: string; email: string; full_name: string; role: number | null }) => {
      return api.post('/users/', data);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
      setShowUserForm(false);
      setEditingUser(null);
    },
  });

  const updateUserMutation = useMutation({
    mutationFn: async ({ id, data }: { id: number; data: Partial<AuthUser> }) => {
      return api.patch(`/users/${id}/`, data);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
      setEditingUser(null);
    },
  });

  const deleteUserMutation = useMutation({
    mutationFn: async (id: number) => {
      return api.delete(`/users/${id}/`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
    },
  });

  const handleUserSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    const data = {
      username: formData.get('username') as string,
      password: formData.get('password') as string,
      email: formData.get('email') as string,
      full_name: formData.get('full_name') as string,
      role: formData.get('role') ? Number(formData.get('role')) : null,
    };

    if (editingUser) {
      updateUserMutation.mutate({ id: editingUser.id, data });
    } else {
      createUserMutation.mutate(data);
    }
  };

  return (
    <div className="admin-page">
      <h1>Администрирование</h1>

      <div className="admin-tabs">
        <button
          className={activeTab === 'users' ? 'active' : ''}
          onClick={() => setActiveTab('users')}
        >
          Пользователи
        </button>
        <button
          className={activeTab === 'roles' ? 'active' : ''}
          onClick={() => setActiveTab('roles')}
        >
          Роли
        </button>
        <button
          className={activeTab === 'audit' ? 'active' : ''}
          onClick={() => setActiveTab('audit')}
        >
          Журнал аудита
        </button>
      </div>

      {activeTab === 'users' && (
        <div className="admin-content">
          <div className="content-header">
            <h2>Управление пользователями</h2>
            <button
              className="btn-add"
              onClick={() => {
                setEditingUser(null);
                setShowUserForm(true);
              }}
            >
              + Добавить пользователя
            </button>
          </div>

          {showUserForm && (
            <div className="form-container">
              <h3>{editingUser ? 'Редактирование' : 'Создание'} пользователя</h3>
              <form onSubmit={handleUserSubmit}>
                <div className="form-row">
                  <label>
                    Логин:
                    <input type="text" name="username" required defaultValue={editingUser?.username} />
                  </label>
                  <label>
                    Email:
                    <input type="email" name="email" required defaultValue={editingUser?.email} />
                  </label>
                </div>
                <div className="form-row">
                  <label>
                    Полное имя:
                    <input type="text" name="full_name" required defaultValue={editingUser?.full_name} />
                  </label>
                  <label>
                    Роль:
                    <select name="role" defaultValue={editingUser?.role || ''}>
                      <option value="">Без роли</option>
                      {roles?.map((role: any) => (
                        <option key={role.id} value={role.id}>
                          {role.name}
                        </option>
                      ))}
                    </select>
                  </label>
                </div>
                {!editingUser && (
                  <div className="form-row">
                    <label>
                      Пароль:
                      <input type="password" name="password" required />
                    </label>
                  </div>
                )}
                <div className="form-actions">
                  <button type="submit" className="btn-primary" disabled={createUserMutation.isPending || updateUserMutation.isPending}>
                    {editingUser ? 'Сохранить' : 'Создать'}
                  </button>
                  <button
                    type="button"
                    className="btn-secondary"
                    onClick={() => {
                      setShowUserForm(false);
                      setEditingUser(null);
                    }}
                  >
                    Отмена
                  </button>
                </div>
              </form>
            </div>
          )}

          <div className="table-container">
            <table className="admin-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Логин</th>
                  <th>Email</th>
                  <th>Полное имя</th>
                  <th>Роль</th>
                  <th>Статус</th>
                  <th>Действия</th>
                </tr>
              </thead>
              <tbody>
                {users?.map((user) => (
                  <tr key={user.id}>
                    <td>{user.id}</td>
                    <td>{user.username}</td>
                    <td>{user.email}</td>
                    <td>{user.full_name}</td>
                    <td>{user.role_name || '—'}</td>
                    <td>{user.is_active ? 'Активен' : 'Неактивен'}</td>
                    <td>
                      <button
                        className="btn-edit"
                        onClick={() => {
                          setEditingUser(user);
                          setShowUserForm(true);
                        }}
                      >
                        Редактировать
                      </button>
                      <button
                        className="btn-delete"
                        onClick={() => {
                          if (confirm(`Удалить пользователя ${user.username}?`)) {
                            deleteUserMutation.mutate(user.id);
                          }
                        }}
                      >
                        Удалить
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {activeTab === 'roles' && (
        <div className="admin-content">
          <h2>Роли системы</h2>
          <div className="roles-list">
            {roles?.map((role: any) => (
              <div key={role.id} className="role-card">
                <h3>{role.name}</h3>
                <p>ID: {role.id}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {activeTab === 'audit' && (
        <div className="admin-content">
          <h2>Журнал аудита</h2>
          <div className="table-container">
            <table className="admin-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Пользователь</th>
                  <th>Действие</th>
                  <th>Таблица</th>
                  <th>ID записи</th>
                  <th>Время</th>
                </tr>
              </thead>
              <tbody>
                {auditLogs?.map((log: any) => (
                  <tr key={log.id}>
                    <td>{log.id}</td>
                    <td>{log.user_full_name || '—'}</td>
                    <td>
                      <span className={`action-badge action-${log.action_type.toLowerCase()}`}>
                        {log.action_type}
                      </span>
                    </td>
                    <td>{log.table_name}</td>
                    <td>{log.record_id}</td>
                    <td>{new Date(log.created_at).toLocaleString('ru-RU')}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
