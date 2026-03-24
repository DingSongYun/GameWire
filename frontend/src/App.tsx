import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { AuthProvider } from './hooks/useAuth';
import AppShell from './components/AppShell';
import ProtectedRoute from './components/ProtectedRoute';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import FeedPage from './pages/FeedPage';
import TrendsPage from './pages/TrendsPage';
import BookmarksPage from './pages/BookmarksPage';
import SourcesAdminPage from './pages/SourcesAdminPage';
import UsersAdminPage from './pages/UsersAdminPage';

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          {/* 公开路由 */}
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />

          {/* 受保护路由 — 包裹在 AppShell 布局中 */}
          <Route
            element={
              <ProtectedRoute>
                <AppShell />
              </ProtectedRoute>
            }
          >
            <Route path="/" element={<FeedPage />} />
            <Route path="/trends" element={<TrendsPage />} />
            <Route path="/bookmarks" element={<BookmarksPage />} />

            {/* 管理员路由 */}
            <Route
              path="/admin/sources"
              element={
                <ProtectedRoute requireAdmin>
                  <SourcesAdminPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/admin/users"
              element={
                <ProtectedRoute requireAdmin>
                  <UsersAdminPage />
                </ProtectedRoute>
              }
            />
          </Route>
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
