# Propuesta de Optimización de Consultas - Mental Data API

Este documento detalla las oportunidades de mejora en el rendimiento de la base de datos MongoDB para el proyecto Mental Data, enfocándose en reducir la carga de CPU y el tiempo de respuesta del Dashboard.

---

## 1. Problemas de Rendimiento Identificados

### A. Cálculos al Vuelo (Agregaciones sin Índices)
En `UsersRepository._buildSubscribersPipeline`, se realizan múltiples transformaciones de datos en cada ejecución:
- Conversión de strings de fecha a objetos `Date` (`$convert`).
- Cálculo de fechas de vencimiento (`$dateAdd`).
- Comparaciones complejas con `$$NOW`.

**Impacto:** MongoDB no puede utilizar índices sobre campos calculados. Esto obliga a un **Colscan** (escaneo completo de la colección), lo cual escala muy mal a medida que crece la base de usuarios.

### B. Ineficiencia en Relaciones (Joins)
El pipeline de `getUsersForGeneralDistribution` utiliza `$lookup` convirtiendo `_id` (ObjectId) a string para coincidir con `userId` (String).
- **Lógica actual:** `let: {"userId": {"$toString": "$_id"}}`
- **Problema:** La conversión de tipo impide que MongoDB realice una unión optimizada a nivel de índice primario.

### C. Tipos de Datos Inconsistentes
Se observa que muchas fechas se almacenan como `String` en lugar de `BSON Date`. 
- **Problema:** Las comparaciones de rango de fechas (`$gte`, `$lte`) sobre strings son considerablemente más lentas y propensas a errores que sobre tipos nativos de fecha.

---

## 2. Plan de Acción: Optimizaciones Propuestas

### I. Materialización de Datos (Prioridad Alta)
**En lugar de calcular, debemos persistir.**

1.  **Persistencia de Fechas:** Migrar todos los campos de fecha (`membershipDate`, `membershipPaymentDate`, `billingDate`, `createdAt`) de `String` a `Date` (BSON).
2.  **Normalización de `billingDate`:** 
    - En lugar de crear un campo nuevo, el proceso de **Backfill** debe asegurar que el campo `lastMembership.billingDate` exista en todos los registros.
    - **Lógica de Backfill:** Si un registro no tiene `billingDate`, se calcula y se guarda como `membershipDate + 31 días`.
    - Esto permite que el índice sea uniforme y apunte siempre al mismo campo nativo.

3.  **Campo `isSubscriptionActive`:** Añadir un booleano que se actualice mediante webhooks o un proceso diario.
    - **Definición de 'Active':** Se debe decidir si los usuarios `free` (como Panchoo) se marcan como `true` o `false`.
    - **Si es `true`:** el campo representaria "Acceso válido a la plataforma". Simplifica saber quién puede entrar, pero requiere un filtro extra para métricas de facturación (`type != "free"`).
    - **Si es `false`:** el campo representaria "Suscriptor de pago actual". Facilita las métricas de negocio directamente, pero trata a los 'free' como "inactivos" en este campo específico.

---

## 2. Estrategia de Migración (Backfill)

Para implementar esto sin romper la producción, se recomienda:

1.  **Script de Normalización:** Un script que recorra la colección y para cada documento:
    - Convierta los strings ISO a `ISODate`.
    - Aplique la lógica: `billDate = billingDate ?? (membershipDate + 31 days)`.
2.  **Actualización de la Capa de Servicio:** Modificar el código que procesa pagos y registros para que SIEMPRE guarde la fecha calculada en el nuevo campo indexado.
3.  **Doble Escritura (Opcional):** Durante una fase de transición, el sistema puede escribir en el formato viejo y el nuevo simultáneamente hasta confirmar que el nuevo campo es confiable.

### II. Normalización de Identificadores
1.  **UserId como ObjectId:** Cambiar el campo `userId` en la colección `hypnosis` de `String` a `ObjectId`.
2.  **Optimización de Lookup:** Al normalizar, el join se simplifica y ultra-optimiza:
    ```json
    {
      "$lookup": {
        "from": "hypnosis",
        "localField": "_id",
        "foreignField": "userId",
        "as": "audioRequests"
      }
    }
    ```

### III. Estrategia de Indexación
Para que las consultas del dashboard sean instantáneas, se recomiendan los siguientes índices compuestos:

**Colección `users`:**
- `db.users.createIndex({ "lastMembership.type": 1, "isSubscriptionActive": 1, "lastMembership.billingDate": 1 })`
- `db.users.createIndex({ "userLevel": 1, "createdAt": -1 })`
- `db.users.createIndex({ "auraEnabled": 1, "createdAt": -1 })`

**Colección `hypnosis`:**
- `db.hypnosis.createIndex({ "userId": 1, "createdAt": -1 })`
- `db.hypnosis.createIndex({ "isAvailable": 1, "createdAt": -1 })`

---

## 3. Ejemplo de Refactorización (Pipeline de Suscriptores)

### Antes (Lento - $O(N)$):
Busca todos los usuarios, los convierte uno por uno y filtra.
```json
[
  { "$addFields": { "payDate": { "$convert": { ... } } } },
  { "$addFields": { "billDate": { "$cond": { ... } } } },
  { "$match": { "$expr": { "$and": [ { "$lte": ["$payDate", "$$NOW"] }, ... ] } } }
]
```

### Después (Rápido - $O(log N)$):
Usa el índice directamente.
```json
[
  {
    "$match": {
      "lastMembership.type": { "$in": ["monthly", "yearly"] },
      "lastMembership.membershipPaymentDate": { "$lte": ISODate("...") },
      "lastMembership.billingDate": { "$gte": ISODate("...") }
    }
  },
  { "$count": "total" }
]
```

---
