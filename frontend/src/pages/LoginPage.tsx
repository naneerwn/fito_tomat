import { FormEvent, useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import './LoginPage.css';

export function LoginPage() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const { login, isLoading, user } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    try {
      await login(username, password);
      const redirectTo = (location.state as { from?: { pathname?: string } })?.from?.pathname ?? '/tasks';
      navigate(redirectTo, { replace: true });
    } catch {
      setError('Неверные учетные данные');
    }
  };

  useEffect(() => {
    if (user) {
      navigate('/tasks', { replace: true });
    }
  }, [navigate, user]);

  return (
    <div className="login-page">
      <form onSubmit={handleSubmit}>
        <h1>АИС «ФитоДиагноз-Томат»</h1>
        <input
          placeholder="Логин"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          autoComplete="username"
        />
        <input
          placeholder="Пароль"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          autoComplete="current-password"
        />
        {error && <p className="error">{error}</p>}
        <button type="submit" disabled={isLoading}>
          {isLoading ? 'Вход...' : 'Войти'}
        </button>
      </form>
    </div>
  );
}

