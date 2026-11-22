import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./stores/auth";
import Layout from "./components/Layout";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import Processos from "./pages/Processos";
import ProcessoDetalhe from "./pages/ProcessoDetalhe";
import Clientes from "./pages/Clientes";
import Prazos from "./pages/Prazos";
import Analise from "./pages/Analise";
import Reunioes from "./pages/Reunioes";
import ReuniaoDetalhe from "./pages/ReuniaoDetalhe";
import Pecas from "./pages/Pecas";
import Financeiro from "./pages/Financeiro";
import Whatsapp from "./pages/Whatsapp";
import Dono from "./pages/Dono";
import Configuracoes from "./pages/Configuracoes";

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
        <Route path="clientes" element={<Clientes />} />
        <Route path="processos" element={<Processos />} />
        <Route path="processos/:id" element={<ProcessoDetalhe />} />
        <Route path="prazos" element={<Prazos />} />
        <Route path="analise" element={<Analise />} />
        <Route path="reunioes" element={<Reunioes />} />
        <Route path="reunioes/:id" element={<ReuniaoDetalhe />} />
        <Route path="pecas" element={<Pecas />} />
        <Route path="financeiro" element={<Financeiro />} />
        <Route path="whatsapp" element={<Whatsapp />} />
        <Route path="dono" element={<Dono />} />
        <Route path="configuracoes" element={<Configuracoes />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
