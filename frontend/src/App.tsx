import { BrowserRouter, Routes, Route } from "react-router-dom";
import { AuthProvider } from "./auth/AuthContext";
import { Layout } from "./components/Layout";
import { RequireAuth } from "./components/RequireAuth";
import { Login } from "./pages/Login";
import { Dashboard } from "./pages/Dashboard";
import { EngagementDetail } from "./pages/EngagementDetail";
import { Tools } from "./pages/Tools";
import { Users } from "./pages/Users";
import { Statistics } from "./pages/Statistics";
import { Credentials } from "./pages/Credentials";

export function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route
            element={
              <RequireAuth>
                <Layout />
              </RequireAuth>
            }
          >
            <Route path="/" element={<Dashboard />} />
            <Route path="/engagements/:engagementId" element={<EngagementDetail />} />
            <Route path="/outils" element={<Tools />} />
            <Route path="/utilisateurs" element={<Users />} />
            <Route path="/statistiques" element={<Statistics />} />
            <Route path="/identifiants" element={<Credentials />} />
          </Route>
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
