import { Navigate, Route, Routes } from 'react-router-dom';
import { Suspense } from 'react';
import { DashboardPage } from './pages/DashboardPage';
import { ImagesPage } from './pages/ImagesPage';
import { DiagnosesPage } from './pages/DiagnosesPage';
import { TasksPage } from './pages/TasksPage';
import { ReportsPage } from './pages/ReportsPage';
import { AdminPage } from './pages/AdminPage';
import { LoginPage } from './pages/LoginPage';
import { MainLayout } from './components/layout/MainLayout';
import { AuthGuard } from './components/auth/AuthGuard';

export default function App() {
  return (
    <Suspense fallback={<div>Загрузка...</div>}>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/"
          element={
            <AuthGuard>
              <MainLayout />
            </AuthGuard>
          }
        >
          <Route index element={<Navigate to="tasks" />} />
          <Route path="dashboard" element={<DashboardPage />} />
          <Route path="images" element={<ImagesPage />} />
          <Route path="diagnoses" element={<DiagnosesPage />} />
          <Route path="tasks" element={<TasksPage />} />
          <Route path="reports" element={<ReportsPage />} />
          <Route path="admin" element={<AdminPage />} />
        </Route>
      </Routes>
    </Suspense>
  );
}

