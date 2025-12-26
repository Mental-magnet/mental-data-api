# Documentación de Queries y Agregaciones

Este documento detalla las consultas a base de datos y pipelines de agregación utilizados en `mental-data-api`, explicando el propósito de cada etapa, campo y la lógica de transformación de datos aplicada en la capa de servicios.

## 1. Users Module
**Repositorio:** `src/modules/v1/users/repository/users_repository.py`
**Servicio:** `src/modules/v1/users/services/users_service.py`
**Colección:** `users`

### `countSuscribers` / `getSuscribers`
**Propósito:** Contar o listar suscriptores activos/inactivos. La lógica de negocio define a un suscriptor activo si su pago es válido hoy y su fecha de facturación (o vencimiento) es futura.

**Pipeline de Agregación (Detallado):**

1.  **Normalización de Fechas (`$addFields`)**:
    *   Convierte los timestamps o strings de la base de datos a objetos `Date` de Mongo para poder compararlos con `$$NOW` (fecha actual).
    *   **`payDate`**: Fecha en que se realizó el pago (`lastMembership.membershipPaymentDate`).
    *   **`rawBillingDate`**: Fecha de facturación registrada (`lastMembership.billingDate`).
    *   **`membershipDateConverted`**: Fecha de inicio de membresía, usada como fallback.

2.  **Cálculo de Vencimiento (`$addFields` -> `billDate`)**:
    *   Define la fecha límite de la suscripción.
    *   **Lógica**: Si existe `rawBillingDate`, se usa. Si no, se calcula sumando **31 días** a `membershipDateConverted`.

3.  **Filtrado de Estado (`$match`)**:
    *   **`lastMembership.type`**: Solo incluye membresías 'monthly' o 'yearly'.
    *   **Condición de Activo**:
        *   `payDate` existe (no es null).
        *   `billDate` existe (no es null).
        *   `payDate <= $$NOW`: El pago ya ocurrió.
        *   `billDate >= $$NOW`: La suscripción aún no vence.

```json
[
  {
    "$addFields": {
      "payDate": {
        "$convert": { "input": "$lastMembership.membershipPaymentDate", "to": "date", "onError": null, "onNull": null }
      },
      "rawBillingDate": {
        "$convert": { "input": "$lastMembership.billingDate", "to": "date", "onError": null, "onNull": null }
      },
      "membershipDateConverted": {
        "$convert": { "input": "$lastMembership.membershipDate", "to": "date", "onError": null, "onNull": null }
      }
    }
  },
  {
    "$addFields": {
      "billDate": {
        "$cond": {
          "if": { "$ne": ["$rawBillingDate", null] },
          "then": "$rawBillingDate",
          "else": {
            "$cond": {
              "if": { "$ne": ["$membershipDateConverted", null] },
              "then": { "$dateAdd": { "startDate": "$membershipDateConverted", "unit": "day", "amount": 31 } },
              "else": null
            }
          }
        }
      }
    }
  },
  {
    "$match": {
      "lastMembership.type": { "$in": ["monthly", "yearly"] },
      "$expr": {
        "$and": [
          { "$ne": ["$payDate", null] },
          { "$ne": ["$billDate", null] },
          { "$lte": ["$payDate", "$$NOW"] },
          { "$gte": ["$billDate", "$$NOW"] }
        ]
      }
    }
  },
  { "$count": "total" } 
]
```

### `getUsersForGeneralDistribution`
**Propósito:** Obtener usuarios aplicando filtros cruzados. Permite saber, por ejemplo, "Usuarios creados en Enero que SÍ han pedido hipnosis".

**Lógica de Transformación (Python Service):**
Una vez obtenidos los usuarios "crudos" de la base de datos, el servicio `_buildGeneralDistribution` procesa la información para generar estadísticas:
1.  **Cálculo de Edad (`_calculateAge`)**: Compara la fecha de nacimiento (`birthdate`) con la fecha actual.
2.  **Bucketing (`_resolveAgeBucket`)**: Agrupa la edad calculada en rangos predefinidos: `0-17`, `18-24`, `25-34`, `35-44`, `45-54`, `55-64`, `65+`.
3.  **Agregación Multidimensional**:
    *   Agrupa por **Idioma** (`user.language`).
    *   Dentro de cada idioma, cuenta totales por **Género** (`user.gender`).
    *   Dentro de cada género, distribuye por **Rango de Edad**.

**Pipeline de Agregación (Detallado):**
1.  **Filtros Base (`$match`)**: (Opcional) Filtra por rango de fecha de creación del usuario (`createdAt`).
2.  **Cruce con Hipnosis (`$lookup`)**:
    *   Busca documentos en la colección `hypnosis`.
    *   **`let`**: Define `userId` con el ID del usuario actual para usarlo dentro del lookup.
    *   **`pipeline` interno**:
        *   `$match`: Busca coincidencias de ID (`$eq: ["$userId", "$$userId"]`).
        *   Filtro de fecha (Opcional): Filtra las *solicitudes* por su propia fecha de creación.
        *   `$limit: 1`: Optimización. Solo nos importa si *existe* al menos una solicitud, no necesitamos traerlas todas.
    *   **`as`**: Guarda el resultado en el campo temporal `audioRequests`.
3.  **Filtro por Existencia (`$match`)**:
    *   Verifica si el array `audioRequests` está vacío o no para determinar si el usuario cumple la condición "tiene hipnosis".
4.  **Limpieza (`$project`)**: Elimina el campo temporal `audioRequests` para no ensuciar el resultado final.

```json
[
  {
    "$match": {
      "createdAt": {
        "$gte": "ISODate('2024-01-01T00:00:00Z')",
        "$lte": "ISODate('2024-12-31T23:59:59Z')"
      }
    }
  },
  {
    "$lookup": {
      "from": "hypnosis",
      "let": { "userId": { "$toString": "$_id" } },
      "pipeline": [
        {
          "$match": {
            "$expr": {
              "$and": [
                { "$eq": ["$userId", "$$userId"] },
                { "$gte": ["$createdAt", "ISODate('...')"] }
              ]
            }
          }
        },
        { "$limit": 1 }
      ],
      "as": "audioRequests"
    }
  },
  {
    "$match": { "audioRequests": { "$ne": [] } }
  },
  { "$project": { "audioRequests": 0 } }
]
```

### `getUsersByPortal`
**Propósito:** Obtener usuarios que se encuentran en un nivel específico del "juego" o aplicación.

**Explicación:**
*   **`userLevel`**: Campo string en la base de datos que indica el nivel actual.
*   Se combina con los pipelines de suscriptores e hipnosis explicados anteriormente si se requieren esos filtros.

```json
[
  {
    "$match": { "userLevel": "1" }
  }
]
```

### `countUsersWithAURA`
**Propósito:** Métrica simple de adopción de la funcionalidad AURA.

**Explicación:**
*   **`auraEnabled`**: Booleano en el perfil del usuario.
*   **`createdAt`**: Filtra cuándo se unió el usuario a la plataforma.

```json
{
  "auraEnabled": true,
  "createdAt": {
    "$gte": "ISODate('2024-01-01T00:00:00Z')",
    "$lte": "ISODate('2024-12-31T23:59:59Z')"
  }
}
```

---

## 2. Hypnosis Module
**Repositorio:** `src/modules/v1/hypnosis/repository/hypnosis_repository.py`
**Servicio:** `src/modules/v1/hypnosis/services/hypnosis_service.py`
**Colección:** `hypnosis`

### `countAudioRequests`
**Propósito:** Contar volumen total de generación de audios.

**Explicación:**
*   Simplemente cuenta documentos en la colección `hypnosis` que caigan dentro del rango de fechas de creación.

```json
{
  "createdAt": {
    "$gte": "ISODate('2024-01-01T00:00:00Z')",
    "$lte": "ISODate('2024-12-31T23:59:59Z')"
  }
}
```

### `countAudioRequestsByListenedStatus`
**Propósito:** Saber cuántos audios han sido consumidos por los usuarios.

**Lógica de Transformación:**
El servicio recibe el parámetro `isListened` (booleano) y lo invierte para consultar el campo `isAvailable` en la base de datos.
*   **Input**: `isListened=True` (Quiero saber cuántos se escucharon).
*   **Query**: `isAvailable=False` (En BD, si no está disponible, es porque ya se consumió/escuchó).

**Explicación Query:**
*   **`isAvailable`**: Este campo funciona de manera inversa para esta lógica.
    *   Si `isAvailable` es `true`, significa que el audio está disponible para ser escuchado (aún **no** escuchado).
    *   Si `isAvailable` es `false`, significa que ya fue consumido/escuchado (o expiró).

```json
{
  "isAvailable": true, // Busca audios NO escuchados
  "createdAt": {
    "$gte": "ISODate('2024-01-01T00:00:00Z')",
    "$lte": "ISODate('2024-12-31T23:59:59Z')"
  }
}
```

---

## 3. Auth Module
**Repositorio:** `src/modules/auth/repository/auth_repository.py`
**Colección:** `auth_sessions`

### `trimSessionsForUser`
**Propósito:** Seguridad y limpieza. Evita que un usuario tenga infinitas sesiones abiertas.

**Lógica de Negocio:**
Se ejecuta típicamente al iniciar sesión. Si el usuario excede el límite de sesiones permitidas (ej. 5), se eliminan las más antiguas para mantener la tabla limpia y forzar el cierre de sesiones olvidadas.

**Explicación Query:**
1.  **Identificación**: Busca sesiones por `user._id` o `user.email`.
2.  **Ordenamiento**: Ordena por fecha de emisión (`issuedAt`) descendente (las más nuevas primero).
3.  **Skip**: Salta las primeras `N` sesiones (las que queremos conservar).
4.  **Selección**: Los documentos restantes son los "sobrantes" u obsoletos.
5.  **Eliminación**: Borra esos documentos específicos por `_id`.

```json
// Paso 1: Encontrar IDs a borrar
db.auth_sessions.find(
  { "$or": [{ "user._id": "..." }, { "user.email": "..." }] },
  { "_id": 1 }
).sort({ "issuedAt": -1 }).skip(5)

// Paso 2: Borrar
db.auth_sessions.deleteMany({ "_id": { "$in": [...] } })
```

### `updateSessionAccess`
**Propósito:** Mantener viva la sesión (Heartbeat).

**Explicación:**
*   Busca por `sessionId` (UUID único).
*   Actualiza `lastAccessAt` y `updatedAt` con el timestamp actual. Esto previene que mecanismos de limpieza automática (TTL) borren sesiones activas.

```json
{
  "q": { "sessionId": "uuid-session-id" },
  "u": {
    "$set": {
      "lastAccessAt": "ISODate('...')",
      "updatedAt": "ISODate('...')"
    }
  }
}
```
