import typing
import fastapi
from ..schemas import user_schema
from ..services import users_service


ROUTER = fastapi.APIRouter()


@ROUTER.get(
    "/count/aura",
    summary="Obtener conteo de usuarios con AURA habilitado",
    response_class=fastapi.responses.JSONResponse,
    response_model=user_schema.UserCountSchema,
    responses={
        200: {"description": "Respuesta exitosa", "model": user_schema.UserCountSchema},
        400: {"description": "Solicitud inválida"},
        500: {"description": "Error interno del servidor"},
    },
)
async def getUsersWithAURA(
    subscriberActive: typing.Annotated[
        typing.Optional[bool],
        fastapi.Query(
            description="Filtra por suscriptores activos (True) o inactivos (False)."
        ),
    ] = None,
    auraEnabled: typing.Annotated[
        bool,
        fastapi.Query(
            description="True cuenta usuarios con aura habilitada, False los que no.",
        ),
    ] = True,
    fromDate: typing.Annotated[
        typing.Optional[int],
        fastapi.Query(description="Timestamp Unix (segundos, entero)"),
    ] = None,
    toDate: typing.Annotated[
        typing.Optional[int],
        fastapi.Query(description="Timestamp Unix (segundos, entero)"),
    ] = None,
) -> user_schema.UserCountSchema:
    """
    Obtiene el número de usuarios con AURA habilitado según los filtros proporcionados.

    Sin rango de fechas devuelve el total histórico de usuarios con aura.
    Al dar fechas, se obtiene los usuarios con aura que se han creado en ese intervalo.
    El parámetro de query `auraEnabled` define si se cuentan usuarios con aura habilitada
    o deshabilitada. Cuando subscriberActive es None se consideran todos los usuarios; True restringe a
    suscriptores activos y False a suscriptores inactivos según la lógica del dashboard.
    """

    # Ambas fechas deben ser provistas juntas o ninguna
    # El operador ^ es el XOR (o exclusivo)
    if (fromDate is None) ^ (toDate is None):
        raise fastapi.HTTPException(
            status_code=400,
            detail="fromDate y toDate deben proporcionarse juntas o no enviarse.",
        )

    if fromDate is not None and toDate is not None and toDate < fromDate:
        raise fastapi.HTTPException(
            status_code=400,
            detail="toDate debe ser mayor o igual que fromDate.",
        )

    # Si se define un rango de fechas el conteo solo incluye usuarios creados dentro de ese intervalo.
    count = await users_service.getUsersWithAURACount(
        isActive=auraEnabled,  # ty:ignore[unknown-argument]
        fromDate=fromDate,  # ty:ignore[unknown-argument]
        toDate=toDate,  # ty:ignore[unknown-argument]
        subscriberActive=subscriberActive,  # ty:ignore[unknown-argument]
    )  # ty:ignore[missing-argument]

    return user_schema.UserCountSchema(count=count, fromDate=fromDate, toDate=toDate)


@ROUTER.get(
    "/count/user-with-hypnosis-request",
    summary="Obtener conteo de usuarios por solicitudes de hipnosis",
    response_class=fastapi.responses.JSONResponse,
    response_model=user_schema.UserCountSchema,
    responses={
        200: {"description": "Respuesta exitosa", "model": user_schema.UserCountSchema},
        400: {"description": "Solicitud inválida"},
        500: {"description": "Error interno del servidor"},
    },
)
async def getUserHypnosisRequestCount(
    subscriberActive: typing.Annotated[
        typing.Optional[bool],
        fastapi.Query(
            description="Filtra por suscriptores activos (True) o inactivos (False)."
        ),
    ] = None,
    hasRequest: typing.Annotated[
        bool,
        fastapi.Query(
            description="True cuenta usuarios con al menos una solicitud, False los que no.",
        ),
    ] = True,
    fromDate: typing.Annotated[
        typing.Optional[int],
        fastapi.Query(description="Timestamp Unix (segundos, entero)"),
    ] = None,
    toDate: typing.Annotated[
        typing.Optional[int],
        fastapi.Query(description="Timestamp Unix (segundos, entero)"),
    ] = None,
) -> user_schema.UserCountSchema:
    """
    Sin rango de fechas retorna el histórico completo.
    Si `hasRequest` es True cuenta usuarios con al menos una solicitud en el rango.
    Si es False cuenta los que no generaron ninguna. subscriberActive sigue la misma lógica del endpoint
    de aura para filtrar por estado de suscripción.
    """

    # Ambas fechas deben ser provistas juntas o ninguna
    if (fromDate is None) ^ (toDate is None):
        raise fastapi.HTTPException(
            status_code=400,
            detail="fromDate y toDate deben proporcionarse juntas o no enviarse.",
        )

    if fromDate is not None and toDate is not None and toDate < fromDate:
        raise fastapi.HTTPException(
            status_code=400,
            detail="toDate debe ser mayor o igual que fromDate.",
        )

    # Con rango de fechas solo se consideran usuarios cuya primera solicitud cae dentro del intervalo.
    count = await users_service.getUsersByHypnosisRequestCount(  # type: ignore
        isActive=hasRequest,  # ty:ignore[unknown-argument]
        fromDate=fromDate,  # ty:ignore[unknown-argument]
        toDate=toDate,  # ty:ignore[unknown-argument]
        subscriberActive=subscriberActive,  # ty:ignore[unknown-argument]
    )

    return user_schema.UserCountSchema(count=count, fromDate=fromDate, toDate=toDate)


@ROUTER.get(
    "/portals",
    summary="Listar portales disponibles",
    response_class=fastapi.responses.JSONResponse,
    response_model=user_schema.UserPortalListSchema,
    responses={
        200: {
            "description": "Respuesta exitosa",
            "model": user_schema.UserPortalListSchema,
        },
        500: {"description": "Error interno del servidor"},
    },
)
async def listUserPortals() -> user_schema.UserPortalListSchema:
    portals = await users_service.getUserPortals()
    return user_schema.UserPortalListSchema(portals=portals)


@ROUTER.get(
    "/distribution/general",
    summary="Obtener distribución general de usuarios",
    response_class=fastapi.responses.JSONResponse,
    response_model=user_schema.UserGeneralDistributionSchema,
    responses={
        200: {
            "description": "Respuesta exitosa",
            "model": user_schema.UserGeneralDistributionSchema,
        },
        400: {"description": "Solicitud inválida"},
        500: {"description": "Error interno del servidor"},
    },
)
async def getGeneralUserDistribution(
    subscriberActive: typing.Annotated[
        typing.Optional[bool],
        fastapi.Query(
            description="Filtra por suscriptores activos (True) o inactivos (False)."
        ),
    ] = None,
    hasHypnosisRequest: typing.Annotated[
        typing.Optional[bool],
        fastapi.Query(
            description="True filtra usuarios con al menos una solicitud de hipnosis."
        ),
    ] = None,
    fromDate: typing.Annotated[
        typing.Optional[int],
        fastapi.Query(description="Timestamp Unix (segundos, entero)"),
    ] = None,
    toDate: typing.Annotated[
        typing.Optional[int],
        fastapi.Query(description="Timestamp Unix (segundos, entero)"),
    ] = None,
    hypnosisFromDate: typing.Annotated[
        typing.Optional[int],
        fastapi.Query(
            description="Timestamp Unix (segundos, entero) aplicado a las solicitudes de hipnosis."
        ),
    ] = None,
    hypnosisToDate: typing.Annotated[
        typing.Optional[int],
        fastapi.Query(
            description="Timestamp Unix (segundos, entero) aplicado a las solicitudes de hipnosis."
        ),
    ] = None,
) -> user_schema.UserGeneralDistributionSchema:
    """
    Entrega la distribución general de usuarios por idioma, género y buckets de edad.
    Sin fechas usa toda la data disponible; con fromDate/toDate solo considera usuarios creados en el intervalo.
    Permite filtrar por estado de suscripción y solicitudes de hipnosis. hypnosisFromDate/hypnosisToDate
    definen el rango de fechas en el que se buscan solicitudes de hipnosis para el filtro.
    """

    if (fromDate is None) ^ (toDate is None):
        raise fastapi.HTTPException(
            status_code=400,
            detail="fromDate y toDate deben proporcionarse juntas o no enviarse.",
        )

    if fromDate is not None and toDate is not None and toDate < fromDate:
        raise fastapi.HTTPException(
            status_code=400,
            detail="toDate debe ser mayor o igual que fromDate.",
        )

    if (hypnosisFromDate is None) ^ (hypnosisToDate is None):
        raise fastapi.HTTPException(
            status_code=400,
            detail="hypnosisFromDate y hypnosisToDate deben proporcionarse juntas o no enviarse.",
        )

    if (
        hypnosisFromDate is not None
        and hypnosisToDate is not None
        and hypnosisToDate < hypnosisFromDate
    ):
        raise fastapi.HTTPException(
            status_code=400,
            detail="hypnosisToDate debe ser mayor o igual que hypnosisFromDate.",
        )

    if (
        hypnosisFromDate is not None or hypnosisToDate is not None
    ) and hasHypnosisRequest is None:
        raise fastapi.HTTPException(
            status_code=400,
            detail="Debe indicar hasHypnosisRequest (True o False) para usar hypnosisFromDate/hypnosisToDate.",
        )

    # Con un rango definido la distribución considera únicamente usuarios creados en ese periodo.
    # hypnosisFromDate/hypnosisToDate acotan las solicitudes de hipnosis utilizadas en el filtro.
    distribution = await users_service.getGeneralUserDistribution(  # type: ignore
        subscriberActive=subscriberActive,  # ty:ignore[unknown-argument]
        hasHypnosisRequest=hasHypnosisRequest,  # ty:ignore[unknown-argument]
        fromDate=fromDate,  # ty:ignore[unknown-argument]
        toDate=toDate,  # ty:ignore[unknown-argument]
        hypnosisFromDate=hypnosisFromDate,  # ty:ignore[unknown-argument]
        hypnosisToDate=hypnosisToDate,  # ty:ignore[unknown-argument]
    )

    return distribution


@ROUTER.get(
    "/distribution/portal",
    summary="Obtener distribución de usuarios por portal",
    response_class=fastapi.responses.JSONResponse,
    response_model=user_schema.UserPortalDistributionSchema,
    responses={
        200: {
            "description": "Respuesta exitosa",
            "model": user_schema.UserPortalDistributionSchema,
        },
        400: {"description": "Solicitud inválida"},
        500: {"description": "Error interno del servidor"},
    },
)
async def getUserPortalDistribution(
    portal: typing.Annotated[
        str,
        fastapi.Query(
            description="Portal (userLevel) para el cual se calculará la distribución"
        ),
    ],
    subscriberActive: typing.Annotated[
        typing.Optional[bool],
        fastapi.Query(
            description="Filtra por suscriptores activos (True) o inactivos (False)."
        ),
    ] = None,
    hasHypnosisRequest: typing.Annotated[
        typing.Optional[bool],
        fastapi.Query(description="True filtra usuarios con solicitudes de hipnosis"),
    ] = None,
    fromDate: typing.Annotated[
        typing.Optional[int],
        fastapi.Query(description="Timestamp Unix (segundos, entero)"),
    ] = None,
    toDate: typing.Annotated[
        typing.Optional[int],
        fastapi.Query(description="Timestamp Unix (segundos, entero)"),
    ] = None,
    hypnosisFromDate: typing.Annotated[
        typing.Optional[int],
        fastapi.Query(
            description="Timestamp Unix (segundos, entero) aplicado a las solicitudes de hipnosis."
        ),
    ] = None,
    hypnosisToDate: typing.Annotated[
        typing.Optional[int],
        fastapi.Query(
            description="Timestamp Unix (segundos, entero) aplicado a las solicitudes de hipnosis."
        ),
    ] = None,
) -> user_schema.UserPortalDistributionSchema:
    """
    Obtiene la distribución de usuarios de un portal específico, agrupada por idioma y género.
    Sin fechas usa todos los usuarios asignados al portal; con fromDate/toDate restringe a los creados en el intervalo.
    Solo se incluyen usuarios con la propiedad userLevel definida; es la única manera de contabilizar un portal.
    hypnosisFromDate/hypnosisToDate delimitan las solicitudes de hipnosis consideradas en el filtro.
    """

    if not portal:
        raise fastapi.HTTPException(
            status_code=400,
            detail="El parámetro portal es obligatorio.",
        )

    if (fromDate is None) ^ (toDate is None):
        raise fastapi.HTTPException(
            status_code=400,
            detail="fromDate y toDate deben proporcionarse juntas o no enviarse.",
        )

    if fromDate is not None and toDate is not None and toDate < fromDate:
        raise fastapi.HTTPException(
            status_code=400,
            detail="toDate debe ser mayor o igual que fromDate.",
        )

    if (hypnosisFromDate is None) ^ (hypnosisToDate is None):
        raise fastapi.HTTPException(
            status_code=400,
            detail="hypnosisFromDate y hypnosisToDate deben proporcionarse juntas o no enviarse.",
        )

    if (
        hypnosisFromDate is not None
        and hypnosisToDate is not None
        and hypnosisToDate < hypnosisFromDate
    ):
        raise fastapi.HTTPException(
            status_code=400,
            detail="hypnosisToDate debe ser mayor o igual que hypnosisFromDate.",
        )

    if (
        hypnosisFromDate is not None or hypnosisToDate is not None
    ) and hasHypnosisRequest is None:
        raise fastapi.HTTPException(
            status_code=400,
            detail="Debe indicar hasHypnosisRequest (True o False) para usar hypnosisFromDate/hypnosisToDate.",
        )

    # Al limitar por fechas solo se incluyen usuarios del portal creados dentro del intervalo indicado.
    # hypnosisFromDate/hypnosisToDate acotan las solicitudes de hipnosis consideradas al filtrar.
    distribution = await users_service.getUserPortalDistribution(  # type: ignore
        portal=portal,  # ty:ignore[unknown-argument]
        fromDate=fromDate,  # ty:ignore[unknown-argument]
        toDate=toDate,  # ty:ignore[unknown-argument]
        subscriberActive=subscriberActive,  # ty:ignore[unknown-argument]
        hasHypnosisRequest=hasHypnosisRequest,  # ty:ignore[unknown-argument]
        hypnosisFromDate=hypnosisFromDate,  # ty:ignore[unknown-argument]
        hypnosisToDate=hypnosisToDate,  # ty:ignore[unknown-argument]
    )

    return distribution
