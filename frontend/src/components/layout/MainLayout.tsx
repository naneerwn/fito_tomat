import { NavLink, Outlet } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';
import './layout.css';

const navItems = [
  { to: '/dashboard', label: 'Дашборд' },
  { to: '/images', label: 'Изображения' },
  { to: '/diagnoses', label: 'Диагностика', roles: ['Агроном', 'Администратор'] },
  { to: '/tasks', label: 'Задачи' },
  { to: '/reports', label: 'Отчёты' },
  { to: '/admin', label: 'Администрирование', roles: ['Администратор'] },
];

export function MainLayout() {
  const { user, logout } = useAuth();
  const roleName = user?.role_name ?? 'Пользователь';

  return (
    <div className="layout">
      <aside>
        <h2>ФитоДиагноз</h2>
        <nav>
          {navItems
            .filter((item) => !item.roles || item.roles.includes(roleName))
            .map((item) => (
              <NavLink key={item.to} to={item.to}>
                {item.label}
              </NavLink>
            ))}
        </nav>
        <div className="user-info">
          <p>{user?.full_name}</p>
          <p className="role">{roleName}</p>
          <button onClick={logout}>Выйти</button>
        </div>
      </aside>
      <main>
        <Outlet />
      </main>
    </div>
  );
}

