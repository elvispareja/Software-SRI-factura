import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout/Layout';
import RutaProtegida from './auth/RutaProtegida';
import Login from './pages/Login/Login';
import Dashboard from './pages/Dashboard/Dashboard';
import ReceptoresList from './pages/Receptores/ReceptoresList';
import ReceptoresForm from './pages/Receptores/ReceptoresForm';
import ArticulosList from './pages/Articulos/ArticulosList';
import ArticulosForm from './pages/Articulos/ArticulosForm';
import ComprobantesList from './pages/Comprobantes/ComprobantesList';
import ComprobanteTraza from './pages/Comprobantes/ComprobanteTraza';
import FacturaForm from './pages/Comprobantes/FacturaForm';
import NotaCreditoForm from './pages/Comprobantes/NotaCreditoForm';
import CotizacionesList from './pages/Cotizaciones/CotizacionesList';
import CotizacionForm from './pages/Cotizaciones/CotizacionForm';
import NotasVentaList from './pages/NotasVenta/NotasVentaList';
import NotaVentaForm from './pages/NotasVenta/NotaVentaForm';
import LiquidacionesList from './pages/Liquidaciones/LiquidacionesList';
import LiquidacionForm from './pages/Liquidaciones/LiquidacionForm';
import GuiasList from './pages/Guias/GuiasList';
import RetencionesList from './pages/Retenciones/RetencionesList';
import RetencionForm from './pages/Retenciones/RetencionForm';
import GuiaRemisionForm from './pages/Guias/GuiaRemisionForm';
import Egresos from './pages/Egresos/Egresos';
import Recurrentes from './pages/Recurrentes/Recurrentes';
import Reportes from './pages/Reportes/Reportes';
import Cuentas from './pages/Cuentas/Cuentas';
import Anticipos from './pages/Anticipos/Anticipos';
import Configuraciones from './pages/Configuraciones/Configuraciones';
import Soporte from './pages/Soporte/Soporte';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />

        <Route element={<RutaProtegida />}>
          <Route path="/" element={<Layout />}>
            <Route index element={<Dashboard />} />

            <Route path="receptores" element={<ReceptoresList />} />
            <Route path="receptores/nuevo" element={<ReceptoresForm />} />
            <Route path="receptores/:id/editar" element={<ReceptoresForm />} />

            <Route path="articulos" element={<ArticulosList />} />
            <Route path="articulos/nuevo" element={<ArticulosForm />} />
            <Route path="articulos/:id/editar" element={<ArticulosForm />} />

            <Route path="comprobantes" element={<ComprobantesList />} />
            <Route path="comprobantes/nuevo" element={<FacturaForm />} />
            <Route path="comprobantes/:id" element={<ComprobanteTraza />} />
            <Route
              path="comprobantes/nota-credito"
              element={<NotaCreditoForm variante="credito" />}
            />
            <Route
              path="comprobantes/nota-debito"
              element={<NotaCreditoForm variante="debito" />}
            />

            <Route path="cotizaciones" element={<CotizacionesList />} />
            <Route path="cotizaciones/nueva" element={<CotizacionForm />} />

            <Route path="notas-venta" element={<NotasVentaList />} />
            <Route path="notas-venta/nueva" element={<NotaVentaForm />} />

            <Route path="liquidaciones" element={<LiquidacionesList />} />
            <Route path="liquidaciones/nueva" element={<LiquidacionForm />} />

            <Route path="guias" element={<GuiasList />} />
            <Route path="guias/nueva" element={<GuiaRemisionForm />} />

            <Route path="retenciones" element={<RetencionesList />} />
            <Route path="retenciones/nueva" element={<RetencionForm />} />

            {/* Gastos y egresos son la misma pantalla: el menú entra por
                pestañas distintas de un mismo módulo. */}
            <Route path="egresos" element={<Egresos />} />
            <Route path="gastos" element={<Egresos />} />
            <Route path="recurrentes" element={<Recurrentes />} />

            <Route path="reportes" element={<Reportes />} />
            <Route path="cuentas" element={<Cuentas />} />
            <Route path="anticipos" element={<Anticipos />} />

            <Route path="configuraciones" element={<Configuraciones />} />
            <Route path="soporte" element={<Soporte />} />
          </Route>
        </Route>

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
