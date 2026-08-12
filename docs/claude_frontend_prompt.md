# Contexto Inicial para Claude (Opus)
Eres un experto desarrollador de interfaces de usuario (Frontend Developer) y un diseñador UI/UX de clase mundial.
Tu objetivo es construir la interfaz web de un **Sistema de Facturación Electrónica para Ecuador (SRI)**.
El sistema debe sentirse de "Siguiente Generación": extremadamente rápido, responsivo y visualmente impactante.

## 1. Stack Tecnológico Elegido
*   **Framework:** React + Vite.
*   **Estilos:** CSS Vanilla (CSS Modules) para un control absoluto. **No uses TailwindCSS**.
*   **Animaciones:** Framer Motion (o animaciones CSS nativas) para micro-interacciones fluidas.
*   **Enrutamiento:** React Router DOM (v6).
*   **Iconografía:** Lucide React (u otra librería moderna y limpia).

## 2. Guía de Diseño (Design System)
Debes crear un diseño con estética **Premium**:
*   **Paleta de colores:** Huye de los colores genéricos (rojo plano, azul aburrido). Utiliza una paleta moderna en formato HSL (Ej. un "Dark Mode" elegante con fondos negro/gris oscuro, tarjetas con efecto "Glassmorphism" sutil y toques de colores vibrantes o neón para las acciones principales como crear factura).
*   **Tipografía:** Utiliza fuentes modernas de Google Fonts (Inter, Roboto, o Outfit). Define jerarquías claras.
*   **Efectos visuales:** Usa desenfoques sutiles (`backdrop-filter: blur`), bordes con opacidad baja para delimitar contenedores sin saturar, y transiciones suaves (hover states) en **todos** los elementos interactivos.
*   **Layout:** "Mobile First", pero aprovechando pantallas grandes. Un menú lateral colapsable (Sidebar) o un Header limpio flotante.

## 3. Módulos a Desarrollar y Detalles Estratégicos

Por favor, empieza desarrollando el código (componentes y estilos) para los siguientes módulos críticos, uno por uno:

### A. Dashboard (Inicio)
Queremos un panel que impresione al usuario nada más entrar.
*   **Componentes:**
    *   Saludo: "Buenas tardes, [Usuario]".
    *   Tarjetas de métricas (Glassmorphism): Facturado este mes ($), Documentos emitidos, Ticket promedio, etc.
    *   Botones de Acción Rápida ("Quick Actions"): "Nueva Factura", "Nuevo Cliente".
    *   Espacio para 2 gráficos hermosos (uno de barras suaves y un Donut chart de distribución).

### B. Módulo Receptores (Clientes)
Debe soportar un Listado y un Modal/Pantalla de Creación.
*   **Listado:** Tabla moderna con búsqueda por texto y filtros (Tipo Persona: Jurídico/Natural; Tipo ID: RUC/Cédula/Pasaporte; Estado: Activado/Desactivado). Menú contextual de "3 puntos" por fila (Editar, Cambiar Estado).
*   **Formulario de Edición/Creación (Dividido en 3 secciones visuales o tabs):**
    *   *Datos Principales:* Tipo ID, Número (con un botón al lado de "Buscar SRI"), Nombre, Correo, Teléfono 1, Dirección, Provincia, Cantón. (Nota: debe haber un toggle visual "Corregir identidad" que simule desbloquear campos bloqueados por seguridad).
    *   *Datos Adicionales:* Nombre comercial, teléfonos/correos secundarios.
    *   *Configuración Comercial:* Método de cancelación (Contado/Crédito), Vendedor, Lista de precios (desplegable), Zona, % Descuento, Límite de crédito.

### C. Módulo Artículos / Servicios (Inventario)
*   **Listado:** Tabla de productos con estado y precio.
*   **Formulario de Creación (3 Tabs):**
    *   *Info Básica:* Toggle (Switch) hermoso entre "Producto" o "Servicio", Código, Nombre, Unidad (Galón, Litro), Detalle descriptivo, Ubicación (Bodega).
    *   *Impuestos:* Selector múltiple de impuestos aplicables (Ej. IVA 15%).
    *   *Costos y Precios:* Campos para Costo compra, Stock (mínimo, reorden, máximo). Y una grilla para 6 "Listas de Precio" donde se ingrese Precio sin impuesto y devuelva visualmente el cálculo con impuesto y margen de utilidad.

### D. Módulo Comprobantes (Facturación)
La vista más compleja y crítica.
*   **Listado:** Tabla con filtros de estado interno (Cancelada, Anulada) y estado SRI (Aceptadas, Rechazadas, No entregadas).
*   **Pantalla de Crear Factura:**
    *   *Banner Superior:* Alerta estilizada "Este Comprobante Electrónico Se Entregará a los servidores de SRI".
    *   *Cabecera:* Emisor (Sucursal), Fecha, y Número de secuencia grande y visible.
    *   *Receptor:* Autocomplete para buscar cliente (con botón rápido "+ Nuevo Cliente"), Vendedor, Canal de venta, Método de pago.
    *   *Detalle (Grilla interactiva):* Buscador de productos (con botón "+ Nuevo Producto"). Tabla con filas dinámicas: Ítem, Cantidad, Precio, IVA, Descuento, Total. Con botón para eliminar fila.

## 4. Entregables Esperados
Para cada módulo que desarrolles, por favor proporciona:
1. El código React (`.jsx` o `.tsx`) dividido en componentes lógicos y reutilizables.
2. El archivo CSS correspondiente (`.module.css` o `index.css`) con todas las variables CSS para mantener el diseño Premium, moderno y con los efectos Glassmorphism mencionados.

Comienza presentándome la estructura de carpetas sugerida y el desarrollo del **Dashboard Principal**.
