# Plan de Desarrollo y Arquitectura: Sistema de Facturación SRI + IA + WhatsApp

Este documento contiene la planificación, arquitectura y lineamientos de desarrollo para construir el nuevo sistema de facturación electrónica. Este archivo está diseñado para que tanto el desarrollador humano, como agentes IA (Claude, Gemini, etc.) tengan el contexto completo del proyecto.

## 1. Visión General del Producto
Construir un sistema de facturación electrónica optimizado para Ecuador (SRI). La interfaz de usuario será **completamente original, moderna y construida desde cero** (no un clon del sistema de referencia). La funcionalidad principal o "Killer Feature" será la **integración nativa con WhatsApp y agentes de Inteligencia Artificial**, lo que permitirá automatizar drásticamente la creación de comprobantes.

---

## 2. Alcance (Módulos Aprobados)
Basados en las directrices de la imagen proporcionada, **únicamente** se desarrollarán los siguientes módulos (se ignoran los tachados):

1. **Inicio (Dashboard)**
2. **Receptores**
   - Clientes
   - Proveedores
   - Transportistas
3. **Artículos / Servicios** (Inventario básico)
4. **Comprobantes Electrónicos**
   - Facturas
   - Liquidación de Compra
   - Guía de Remisión
   - Notas de Crédito / Débito
5. **Cotización** (Proformas)
6. **Notas de Venta** (Régimen RIMPE Negocios Populares)
7. **Configuraciones**
   - Perfil / Empresa
   - Cuentas Bancarias
   - Firmas Electrónicas (SRI Certificado .p12 / .pfx)
   - Impuestos y Leyendas
8. **Soporte Técnico**

> **Módulos Excluidos Explícitamente:** Recurrentes, Egresos, Anticipos, Cuentas Pendientes, Reportes y Calendario.

---

## 3. Arquitectura del Sistema e Integración IA + WhatsApp

### 3.1. Flujo de IA + WhatsApp
El objetivo es que el usuario final apenas necesite abrir la interfaz web, pudiendo hacer el 90% del trabajo desde su celular.
- **Ingesta de Datos:** El usuario envía al bot de WhatsApp:
  - Un texto libre: *"Haz una factura de 50 dólares a Juan Pérez, RUC 17XXXXXX por servicios de consultoría"*.
  - Un audio (procesado por Whisper/Speech-to-Text).
  - Una foto de un RUC, cédula, o un recibo físico (procesado por Visión/OCR).
- **Extracción Inteligente (LLM):** El modelo extrae entidades estructuradas (Monto, Descripción, Identificación, etc.).
- **Validación SRI Automática:** Con el RUC extraído, el backend consulta el API pública del Registro Civil/SRI para autocompletar Razón Social y Dirección.
- **Transmisión SRI:** El sistema backend arma el XML, lo firma con el `.p12` del usuario y lo envía al WebService del SRI.
- **Respuesta:** El bot envía de vuelta el PDF de la factura autorizada al usuario de WhatsApp, y opcionalmente, la envía directamente al cliente final.

### 3.2. Diseño de la Interfaz (Custom UI) y Dashboard
- **Filosofía:** "Mobile First", minimalista y centrada en la velocidad. A diferencia de la barra lateral oscura y recargada de la versión anterior, nuestra propuesta será limpia y modular.
- **Dashboard (Inicio):**
  - **Saludo Personalizado:** "Buenas tardes, [Usuario]".
  - **Acciones Rápidas (Quick Actions):** Botones destacados para "Conexión Tributaria", "Crear Receptor", "Crear Inventario", "Crear Factura".
  - **Estado del Plan:** Barra de progreso visual (ej. Uso de documentos: 21/30), detalles de pagos y fechas de vencimiento.
  - **Métricas y KPIs Clave (Tarjetas):** Facturado este mes ($), Documentos del mes, Ticket promedio ($), Documentos del año.
  - **Gráficos:** Gráfico de líneas suavizado para "Facturación mensual" y un gráfico de anillo (Donut chart) para la "Distribución por tipo de documento".
  - **Resumen Numérico:** Contadores rápidos de Clientes, Productos y Servicios registrados.
- **Experiencia de Usuario (UX):** Animaciones fluidas, *Command Palettes* (estilo Spotlight) para evitar clics innecesarios y navegación rápida entre las secciones no excluidas.

---

## 4. Modelo de Datos y Estructuras Clave

### 4.1. Configuraciones de la Cuenta / Empresa
- `Tenant` o `Empresa`: RUC, Razón Social, Nombre Comercial, Dirección Matriz, Obligado a Contabilidad (Boolean), Régimen (General, RIMPE, etc.).
- `Establecimiento` y `PuntoEmision`: Para gestionar secuencias de facturas (ej. `001-001`).
- `FirmaElectronica`: Archivo (`.p12`/`.pfx`) almacenado de forma segura, contraseña encriptada, fecha de expiración.

### 4.2. Catálogo: Receptores (Ultra Detallado)
La estructura de creación de Receptores (Clientes, Proveedores, Transportistas) se dividirá lógicamente en tres secciones/pestañas, tal como lo expone la nueva versión del sistema de referencia, para mapear exactamente a nuestra Base de Datos:

**Listado y Acciones (Vista Principal):**
- **Filtros:** Búsqueda por texto, Estado (Todos, Activado, Desactivado), Tipo Persona (Jurídico, Natural), Tipo Identificación (RUC, Cédula, Pasaporte, Consumidor Final, Identificación exterior). Paginación ajustable (10, 20, 30, 40, 50).
- **Acciones Generales:** Descargar Listado, Descargar para importar, Importar.
- **Acciones por Registro:** Editar, Cambiar Estado, Sucursales.

**A. Datos Obligatorios Tributación y Otros (Datos Principales):**
- `Tipo Identificación`: Cédula de ciudadanía, RUC, Pasaporte, Consumidor Final, Identificación del Exterior.
- `Número Identificación`: (Único) Con botón de **Búsqueda automática al SRI** para autocompletar. *Nota de UI: Estos campos se bloquean al emitir un documento, mostrando una alerta. Requiere usar el switch "Corregir identidad" para forzar un cambio por error de digitación.*
- `Nombre`: Razón Social o Nombres Completos (Autocompletado o editable).
- `Correo`: Correo principal.
- `Teléfono #1`: Número de contacto principal.
- `Dirección`: Dirección fiscal (obligatoria para el XML).
- `Provincia` y `Cantón`: Listas desplegables geográficas.

**B. Datos Opcionales (Datos Adicionales):**
- `Nombre Comercial`: Nombre fantasía de la empresa (si aplica).
- `Teléfono #2`: Número de contacto alternativo.
- `Correo #2` y `Correo #3`: Cuentas de email adicionales.

**C. Configuración (Datos Financieros y Comerciales):**
- `Método Cancelación`: Forma de pago predeterminada (ej. Contado, Crédito).
- `Vendedor`: Asignación a un vendedor específico.
- `Precio a facturar`: Lista de precios asignada por defecto.
- `Zona`: Categorización geográfica.
- `% Descuento`: Descuento global porcentual.
- `Código`: Identificador interno.
- `Crédito máximo`: Límite de crédito otorgado.

### 4.3. Catálogo: Artículos / Servicios (Ultra Detallado)
El listado principal permite buscar, filtrar y exportar/importar. La creación se divide en tres secciones:

**A. Información Básica:**
- **Tipo (Toggle):** Producto o Servicio.
- **Código y Codificación:** Código interno y tipo de codificación (ej. Operadora de transporte).
- **Nombre:** Nombre principal del ítem.
- **Unidad de medida:** Ej. Galón, Unidad, Litro.
- **Detalle:** Descripción ampliada para la factura.
- **Ubicación:** Detalles físicos de bodega (ej. Bodega Principal / Estante B).

**B. Impuestos:**
- **Selección de Impuesto:** Múltiples tipos aplicables (ej. IVA 15%, No Objeto, Exento).

**C. Costos y Precios:**
- **Inventario:** Costo compra, Stock mínimo, Reorden (punto de pedido), Stock máximo.
- **Listas de Precios (P1 a P6):** Tabulador múltiple donde cada fila calcula automáticamente: Precio sin impuesto, Precio con impuesto y % de Utilidad.

### 4.4. Transaccional: Comprobantes (Facturas)
**Listado de Facturas (Vista Principal):**
- **Filtros Avanzados:** Por Número, Método (Contado/Crédito), Estado Interno (Cancelada, Pendiente, Anulada), Tributación SRI (No Entregado, Aceptadas, Rechazadas, Desconocido), Paginación (10 a 50).
- **Acciones:** Ver PDF, Imprimir, Descargar (XML/PDF), Comprobante Factura (ver detalles).

**Creación de Factura:**
- **Banner de Estado:** Indicador visual (ej. "Este Comprobante Electrónico Se Entregará a los servidores de SRI").
- **Cabecera:** Selección de Empresa/Sucursal (Emisor), Fecha de Emisión, Secuencial visual (ej. FED 46).
- **Receptor y Opciones:**
  - Búsqueda/Selección de Cliente (con botón para crear "+ Nuevo Cliente" incrustado).
  - Canal o Medio de venta.
  - Vendedor asignado.
  - Medio de pago (Contado, Crédito, etc.).
  - Toggles adicionales: Contacto, Taller, Otras Opciones.
- **Productos y Servicios:**
  - Selección de Bodega.
  - Toggle rápido para buscar "Productos" o "Servicios".
  - Buscador predictivo de ítems con botón para crear "+ Nuevo Producto" incrustado.
  - Grilla de Detalles: Ítem, Cantidad, Precio, Precio IVA, Subtotal, Descuento, Total, Impuestos, Total Línea y Acciones (eliminar fila).

### 4.5. Transaccional: Liquidación de Compra
**Creación de Liquidación:**
- **Cabecera (Documento):** Selección de Empresa/Sucursal, Fecha de Emisión y Secuencial.
- **Receptor y Opciones:**
  - Búsqueda/Selección de Proveedor (con opción rápida de crear).
  - Canal o Medio de venta.
  - Vendedor asignado.
  - Medio de pago (Contado, etc.).
- **Opciones de Importación:** Botones para "Importar XML" o "Importar PDF / Foto".

### 4.6. Transaccional: Comprobante de Retención
**Creación de Retención:**
- **Cabecera (Documento):** Selección de Sucursal, Fecha de Emisión y Secuencial.
- **Receptor:** Búsqueda de Cliente o Sujeto Retenido.
- **Detalle de Impuestos (Grilla):** Impuesto (Renta, IVA, ISD), Código Retención, Base Imponible, Porcentaje, Total retenido. Botón para "+ Añadir impuesto".

### 4.7. Transaccional: Guía de Remisión
**Creación de Guía de Remisión:**
- **Datos del Transporte:**
  - Fecha Inicio y Fecha Fin.
  - Motivo Traslado y Ruta Traslado.
  - Documento Aduanero (opcional).
  - Tipo de Transporte (Público, Privado).
- **Datos del Conductor:** Búsqueda de Transportista, Identificación, Placa Vehículo, Correo, Dirección.
- **Puntos de Partida y Llegada:** Provincia, Cantón y Dirección exacta de partida y llegada.
- **Productos y Servicios:** Grilla para añadir los ítems transportados (Búsqueda de producto, Cantidad).

### 4.8. Transaccional: Cotización (Proformas)
**Listado y Creación:**
- **Listado:** Filtros por Método (Contado/Crédito), Estado (Cancelado/Pendiente/Anulada), y Búsqueda por número.
- **Creación:** Estructura visualmente idéntica a "Facturas", con sección de "Documento", "Receptor y Opciones", y "Productos y Servicios".

### 4.9. Transaccional: Notas de Venta (Régimen RIMPE)
**Listado y Creación:**
- **Listado:** Filtros similares a Facturas y Cotizaciones (Estado, Método).
- **Creación:** Estructura seleccionando Cliente, Canal de venta, y grilla de Productos/Servicios adaptada al formato de Negocios Populares.

---

## 5. Fases de Desarrollo (Roadmap)

### Fase 1: Arquitectura Base y Backend Core
1. Inicializar el repositorio (Frontend y Backend).
2. Configurar Base de Datos (ej. PostgreSQL / Supabase / Firebase).
3. Desarrollar el módulo de Autenticación y el modelo de `Configuraciones` (Carga de P12 y datos de Empresa).

### Fase 2: Motor SRI (El Núcleo Crítico)
1. Desarrollar lógica de generación de esquemas XML basados en las fichas técnicas del SRI.
2. Implementar módulo de firmado criptográfico (XAdES-BES).
3. Integración con el WebService del SRI (entornos de PRUEBAS y PRODUCCIÓN) para Recepción y Autorización.
4. Generador de PDF (Ride).

### Fase 3: Catálogos y UX Web
1. Crear el Custom UI para el Dashboard (Inicio).
2. Desarrollar CRUD de `Receptores` (Clientes, Proveedores, Transportistas) conectados al API del Registro Civil/SRI.
3. Desarrollar CRUD de `Artículos / Servicios`.

### Fase 4: Integración Omnicanal (IA + WhatsApp)
1. Conexión de Webhooks con Meta Graph API (WhatsApp Business).
2. Creación del Agente Orquestador (Claude/Gemini) para interpretar texto/audio/imágenes.
3. Conectar el output del LLM con el Motor SRI interno para emitir la factura de forma autónoma.
4. Diseñar respuestas ricas del Bot y envío de PDFs.

### Fase 5: Módulos Complementarios
1. Desarrollo de vistas para Liquidación de Compra, Guías de Remisión y Notas de Crédito/Débito.
2. Desarrollo de Cotizaciones y Notas de Venta.
3. Módulo de Soporte Técnico (Tickets o integraciones directas a un chat de atención).

---

## 6. Próximos Pasos Ejecutivos
- [ ] Definir el Stack de Tecnologías exactas que utilizaremos.
- [ ] Iniciar el setup del proyecto en el workspace.
- [ ] Comenzar con la Fase 1 (Base de Datos y Motor SRI).
