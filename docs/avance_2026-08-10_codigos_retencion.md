# Avance: Códigos de Retención (Catálogo ATS)

**Fecha:** 2026-08-10
**Objetivo:** Completar y verificar los códigos numéricos de retención en la fuente (Renta e IVA) según el Catálogo ATS oficial del SRI, vigente a partir de la resolución NAC-DGERCGC26-00000009 (marzo 2026).

## Decisiones y Cambios Realizados

### 1. Impuesto a la Renta (`codigos_retencion.py`)
Se identificó que el backend ya contaba con los porcentajes de retención actualizados al 2026, pero faltaban los códigos ATS oficiales para 14 conceptos. Se procedió a asignarlos:

- **Reasignación del Código 332:** En la resolución anterior, el 332 correspondía al 2,75% (tarifa ahora derogada). En el catálogo 2026, el 332 se reutiliza para "RIMPE Negocios Populares" (0%) y otras compras no sujetas. Se implementó este cambio.
- **Sociedades vs. Personas Naturales:** Se agregaron los códigos `303A` (servicios, 5%) y `303B` (comisiones, 5%) para sociedades, distinguiéndolos del 10% clásico.
- **Regla General:** Se asignó el código `340` (3%) para pagos sin porcentaje específico.
- **Otros:** `304E` (docencia, 10%), `314A` (regalías, 10%), `343A` (energía eléctrica, 2%), `343B` (construcción, 2%), `304C` (deportistas/artistas, 10%), entre otros.

### 2. IVA (`codigos_retencion.py`)
El bloque de IVA no tenía códigos asignados para prevenir rechazos por discrepancias entre versiones del XML (v1.0.0 vs v2.0.0). Se confirmó que el sistema emite retenciones en la **versión 1.0.0**, por lo que se asignaron los códigos estándar del SRI correspondientes a esta versión:

- `721` (0%)
- `723` (10%)
- `725` (20%)
- `727` (30% - bienes)
- `729` (70% - servicios)
- `731` (100% - profesionales, arrendamiento a PN, dietas)

Todos los códigos de IVA pasaron a marcarse con `verificado=True`.

### 3. Ajuste de Pruebas (`test_retenciones.py`)
Se adaptaron las pruebas unitarias para proteger la nueva integridad del catálogo:
- `test_la_tarifa_derogada_del_275_ya_no_existe`: Se actualizó para validar que el código `332` ahora retiene el 0%.
- `test_todos_los_conceptos_tienen_codigo_y_estan_verificados`: Se reemplazó la prueba antigua (que validaba que algunos estuvieran en blanco) por una aserción estricta (`concepto.codigo != ""`) que asegura que ningún concepto pueda existir sin su respectivo código ATS.
- Se agregaron comprobaciones para `303A` (5%), `340` (3%) y `727` (30%).

## Estado
**Completado y Probado.** Las 22 pruebas unitarias correspondientes a la retención pasaron exitosamente. El sistema ahora emite el `codigoRetencion` exacto para el XML, eliminando la necesidad de que el usuario lo escriba manualmente en la interfaz en el 100% de los casos tipificados.
