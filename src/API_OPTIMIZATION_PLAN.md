# Plan de Optimización de la API (Sin tocar la Base de Datos)

Este documento detalla las mejoras tácticas en el código Python para aumentar la velocidad de procesamiento y evitar bloqueos en el hilo principal asíncrono.

## Archivos Involucrados
1.  `src/modules/v1/users/repository/users_repository.py`: Optimización de validación masiva.
2.  `src/modules/v1/users/services/users_service.py`: Optimización de lógica CPU-bound (edad) y concurrencia.

---

## Paso a Paso

### 1. Validación Masiva con Pydantic `TypeAdapter`
**Ubicación:** `src/modules/v1/users/repository/users_repository.py`
- **Cambio:** Uso de `TypeAdapter(list[UserSchema])` para todas las devoluciones de listas.
- **Razón:** Pydantic V2 procesa validaciones de listas en Rust, siendo significativamente más rápido que bucles manuales.

### 2. Proyecciones Estrictas (Data Minimization)
**Ubicación:** `src/modules/v1/users/repository/users_repository.py`
- **Cambio:** Añadido `$project` en MongoDB para traer solo los campos definidos en `UserSchema`.
- **Razón:** Reduce el uso de red y memoria al ignorar campos no presentes en el esquema, manteniendo toda la información importante para el Frontend.

### 3. Optimización de Cálculo de Edad (String Slicing)
**Ubicación:** `src/modules/v1/users/services/users_service.py` (`_calculateAge`)
- **Cambio:** Extraer el año del string `birthdate` usando `birthdate[0:4]`.
- **Razón:** Ahorro masivo de tiempo al evitar el parseo completo de ISO dates y zonas horarias para miles de registros.

### 4. Desbloqueo del Event Loop (Threading)
**Ubicación:** `src/modules/v1/users/services/users_service.py`
- **Cambio:** Envolver `_buildGeneralDistribution` en `anyio.to_thread.run_sync`.
- **Razón:** Evita que el procesamiento estadístico pesado bloquee la API, permitiendo atender otras peticiones en paralelo.

### 4. Caché con Stampede Protection (Verificación)
**Ubicación:** `src/modules/v1/users/services/users_service.py`
- **Acción:** Asegurar que todas las funciones de agregación pesadas usen `@aiocache.cached_stampede` para evitar picos de carga si el caché expira.

---

## Resultados Esperados
- **CPU:** Menor consumo por petición gracias a Pydantic y el slicing de strings.
- **Latencia:** Respuesta más rápida al Dashboard al reducir el tiempo de serialización/validación.
- **Concurrencia:** Mayor capacidad de respuesta de la API bajo carga pesada al no bloquear el loop de FastAPI.
