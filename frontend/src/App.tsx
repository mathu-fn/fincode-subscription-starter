import { Navigate, Route, Routes } from "react-router-dom";

import { Layout } from "./components/Layout";
import { PageLoading } from "./components/PageLoading";
import { RequireAuth } from "./components/RequireAuth";
import { AuthProvider, useAuth } from "./hooks/useAuth";
import { AccountPage } from "./pages/AccountPage";
import { HomePage } from "./pages/HomePage";
import { LandingPage } from "./pages/LandingPage";
import { LoginPage } from "./pages/LoginPage";
import { NotFoundPage } from "./pages/NotFoundPage";

function RootRoute() {
  const { user, loading } = useAuth();
  if (loading) {
    return <PageLoading />;
  }
  return user ? <HomePage /> : <LandingPage />;
}

export function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/" element={<RootRoute />} />
          <Route
            path="/account"
            element={
              <RequireAuth>
                <AccountPage />
              </RequireAuth>
            }
          />
          <Route
            path="/plans"
            element={
              <RequireAuth>
                <Navigate to="/#plans" replace />
              </RequireAuth>
            }
          />
          <Route
            path="/cards"
            element={
              <RequireAuth>
                <Navigate to="/#cards" replace />
              </RequireAuth>
            }
          />
          <Route
            path="/subscription"
            element={
              <RequireAuth>
                <Navigate to="/#subscription" replace />
              </RequireAuth>
            }
          />
          <Route
            path="/history"
            element={
              <RequireAuth>
                <Navigate to="/#history" replace />
              </RequireAuth>
            }
          />
          <Route path="/404" element={<NotFoundPage />} />
          <Route path="*" element={<Navigate to="/404" replace />} />
        </Route>
      </Routes>
    </AuthProvider>
  );
}
