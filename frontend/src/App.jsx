import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./stores/auth";
import Layout from "./components/Layout";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import Processos from "./pages/Processos";

function Protegido({ children }) {
  const user = useAuth((s) => s.user);
  if (!user) return <Navigate to="/login" replace />;
  return children;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        path="/"
        element={
          <Protegido>
            <Layout />
          </Protegido>
        }
      >
        <Route index element={<Dashboard />} />
        <Route path="processos" element={<Processos />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
