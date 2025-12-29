# Estrategia Maestra de Caching y Optimización - Mental Data API

**Estado:** Definición Arquitectónica  
**Objetivo:** Eliminar la carga de CPU en MongoDB generada por el Dashboard de Analítica y reducir la latencia de respuesta de segundos a milisegundos.

---

## 1. El Problema (Diagnóstico)

El Dashboard de Mental Data requiere calcular métricas históricas complejas (ej. "Usuarios inactivos que escucharon hipnosis el último mes") cada 30-60 segundos.
*   **Síntoma:** CPU de MongoDB al 100% y tiempos de espera (timeouts) en el Frontend.
*   **Causa Raíz:** MongoDB está "re-calculando el mundo" en cada petición. Las agregaciones (`$lookup`, `$convert`) son costosas y se repiten idénticas para cada usuario que mira el dashboard.

---

## 2. La Solución en Dos Fases

Para solucionar esto, implementaremos dos estrategias complementarias. Es crucial entender la diferencia entre ellas:

### Fase 1: Cache Reactivo (Mitigación Inmediata)
*Implementada actualmente.*
*   **Concepto:** "Si ya calculé esto hace 5 minutos, no lo vuelvas a calcular".
*   **Tecnología:** `fastapi-cache2` (In-Memory / Redis).
*   **Cómo funciona:**
    1.  El **primer** usuario hace la petición -> La API calcula en DB (Lento, alto CPU).
    2.  La API guarda el resultado (JSON) en memoria por 1 hora.
    3.  Los siguientes **1,000 usuarios** reciben la copia de memoria (Instantáneo, 0 CPU).
*   **Resultado:** Reduce la frecuencia de picos de CPU de "constante" a "una vez por hora".

### Fase 2: Cache Proactivo (Arquitectura Final)
*Objetivo a implementar con Workers.*
*   **Concepto:** "Mantengamos el número actualizado siempre, para no tener que calcular nada nunca".
*   **Tecnología:** Redis Counters + Background Workers.
*   **Cómo funciona:**
    1.  Cuando ocurre un evento (ej. nueva hipnosis), incrementamos un contador simple en Redis `INCR stats:hypnosis:total` (+1).
    2.  Cuando el usuario pide el dato, la API solo lee ese número de Redis.
*   **Resultado:** Elimina por completo la necesidad de hacer queries de conteo a la DB para lectura. Costo de lectura `O(1)`.

---

## 3. Matriz de Decisión: ¿Qué técnica usar para qué dato?

No todos los datos sirven para la Fase 2 (Proactiva). Usamos un criterio de complejidad.

| Tipo de Dato | Ejemplo | Estrategia Elegida | ¿Por qué? |
| :--- | :--- | :--- | :--- |
| **Contadores Simples (KPIs)** | *Total de Hipnosis, Total Suscriptores Activos* | **Fase 2 (Proactiva)** | Son fáciles de incrementar (+1) en tiempo real. Máxima velocidad. |
| **Analítica Compleja** | *Distribución de Usuarios por Edad y Género* | **Fase 1 (Reactiva)** | Tienen demasiadas combinaciones de filtros para pre-calcular todas. Mejor calcular bajo demanda y cachear el resultado. |
| **Listas Estáticas** | *Lista de Portales* | **Fase 1 (Reactiva)** | Cambian muy poco (meses). Ideal para cache simple de larga duración (TTL 24h). |

---

## 4. Detalle de Implementación: Fase 2 (Worker + Redis)

Esta sección detalla cómo funciona la arquitectura de contadores proactivos.

### A. Roles y Responsabilidades

*   **El Servicio (API):** Responsable de la **Velocidad**. Actualiza el contador en Redis en el momento exacto (Real-time) cuando ocurre una escritura.
*   **El Worker (Background):** Responsable de la **Verdad**. Corre cada noche para contar la DB real y corregir cualquier desviación en Redis (Reconciliación).

### B. Buckets de Tiempo (Time Series)
Para métricas históricas, usamos "barriles" (buckets) de tiempo en Redis para no perder el detalle sin saturar la DB.

| Bucket Pattern | Ejemplo Clave | TTL | Uso en Dashboard |
| :--- | :--- | :--- | :--- |
| `stats:<kpi>:total` | `stats:hypnosis:total` | ∞ | Número grande de cabecera. |
| `stats:<kpi>:YYYY-MM` | `stats:hypnosis:2024-12` | 18 Meses | Gráficos de comparativa mensual. |
| `stats:<kpi>:YYYY-MM-DD` | `stats:hypnosis:2024-12-26` | 60 Días | Gráfico de línea "Últimos 30 días". |

---

## 5. Prerrequisitos Técnicos

1.  **Migración de Fechas (DB):**
    *   Para que el Worker pueda contar eficientemente ("Dame las hipnosis de ayer"), el campo `createdAt` debe ser `ISODate`, no `String`.
    *   *Estado:* Pendiente (Prioridad Alta).
2.  **Infraestructura Redis:**
    *   Se requiere una instancia de Redis persistente para producción.
    *   *Estado:* Configurado "In-Memory" para desarrollo local, pendiente activar Redis en PROD.

---

## 6. Plan de Acción Resumido

1.  **[HECHO]** Aplicar Cache Reactivo (`@cache`) a todos los endpoints pesados del dashboard. (Esto apaga el incendio actual).
2.  **[PENDIENTE]** Migrar fechas de String a Date en MongoDB.
3.  **[PENDIENTE]** Crear Worker de Reconciliación nocturno.
4.  **[PENDIENTE]** Migrar KPIs principales a Cache Proactivo (Redis Counters).
