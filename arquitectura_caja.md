# ESPECIFICACIONES DE NEGOCIO: CONTROL DE CAJA Y GANANCIA REAL

## 1. Moneda Base y Conversión
* Base de Datos: Opera estrictamente en Bolívares (Bs) para cuadrar con Pago Móvil.
* Capa de Referencia: Se añade `tasa_dolar_dia` en `Configuracion` para reportes bimoneda visuales y actualización de límites.

## 2. Fórmulas Financieras
* Ganancia Real Diaria = (Ventas Animalitos - Premios Animalitos) + Comisión Mercados (5%).
* Fondo Semilla Mínimo = Límite Máximo Apuesta × Multiplicador × Factor de Seguridad (2 o 3 sorteos).

## 3. Reglas de Negocio Aprobadas
* Regla 1 (Fondo Semilla Intocable): Si hay ganancia, el excedente va a utilidades y la nueva caja abre con el fondo óptimo exacto. Si hay pérdida, la caja abre disminuida (déficit).
* Regla 2 (Alerta Crítica): Si la caja baja del 40% del fondo semilla, se alerta al administrador y se reducen temporalmente los límites de apuesta.
* Regla 3 (Cierre Híbrido): Cierre automático a las 11:59 PM (vía Flask-APScheduler) y opción de cierre manual en el panel para contingencias.

## 4. Estructura de Modelos a Implementar
* `Configuracion`: Agregar `tasa_dolar_dia`, `fondo_semilla_optimo` y `caja_real_disponible`.
* `SesionCaja`: Nueva tabla para el histórico de auditoría (`fecha_apertura`, `monto_apertura_bs`, `monto_cierre_sistema`, `monto_cierre_real`, `discrepancia`, `estado`).

##"Vamos a implementar el sistema de sesiones de caja basándonos en el resumen aprobado de *Bolívares, cierre híbrido y la tabla SesionCaja."