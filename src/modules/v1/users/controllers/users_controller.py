import typing
import fastapi
import logging

from src.modules.v1.shared.utils import dates as dates_utils
from ..schemas import user_schema
from ..services import users_service

LOGGER = logging.getLogger("uvicorn").getChild("v1.users.controllers.users")


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
    isActive: typing.Annotated[bool, fastapi.Query()] = True,
    fromDate: typing.Annotated[typing.Optional[str], fastapi.Query(description="Formato: cadena ISO 8601 (YYYY-MM-DDTHH:MM:SSZ)")] = None,
    toDate: typing.Annotated[typing.Optional[str], fastapi.Query(description="Formato: cadena ISO 8601 (YYYY-MM-DDTHH:MM:SSZ)")] = None,
) -> user_schema.UserCountSchema:
    """
    Obtiene el número de usuarios con AURA habilitado según los filtros proporcionados.

    Al dar fechas, se obtiene los usuarios con aura que se han creado en ese rango de fechas.
    """

    # Ambas fechas deben ser provistas juntas o ninguna
    # El operador ^ es el XOR (o exclusivo)
    if (fromDate is None) ^ (toDate is None):
        raise fastapi.HTTPException(
            status_code=400,
            detail="fromDate y toDate deben proporcionarse juntas o no enviarse.",
        )
    
    # Verificamos el formato ISO de las fechas si son provistas
    if fromDate is not None and not dates_utils.verifyISOFormat(fromDate):
        raise fastapi.HTTPException(
            status_code=400,
            detail=f"La fecha fromDate proporcionada ({fromDate}) no tiene formato ISO.",
        )

    if toDate is not None and not dates_utils.verifyISOFormat(toDate):
        raise fastapi.HTTPException(
            status_code=400,
            detail=f"La fecha toDate proporcionada ({toDate}) no tiene formato ISO.",
        )

    # toDate debe ser mayor o igual a fromDate
    # comparamos usando timestamp para ser más precisos
    if fromDate is not None and toDate is not None:
        fromDateTimestamp = dates_utils.convertISOtoTimestamp(fromDate)
        toDateTimestamp = dates_utils.convertISOtoTimestamp(toDate)

        if toDateTimestamp < fromDateTimestamp:
            raise fastapi.HTTPException(
                status_code=400,
                detail="toDate debe ser mayor o igual que fromDate.",
            )

    count = await users_service.getUsersWithAURACount(
        isActive=isActive,
        fromDate=fromDate,
        toDate=toDate,
    )

    return user_schema.UserCountSchema(count=count , fromDate=fromDate, toDate=toDate)



@ROUTER.get(
    "/count/without-hypnosis-request",
    summary="Obtener conteo de usuarios sin solicitud de hipnosis",
    response_class=fastapi.responses.JSONResponse,
    response_model=user_schema.UserCountSchema,
    responses={
    200: {"description": "Respuesta exitosa", "model": user_schema.UserCountSchema},
    400: {"description": "Solicitud inválida"},
    500: {"description": "Error interno del servidor"},
    },
)
async def getUsersWithoutHypnosisRequest(
    fromDate: typing.Annotated[typing.Optional[str], fastapi.Query(description="Formato: cadena ISO 8601 (YYYY-MM-DDTHH:MM:SSZ)")] = None,
    toDate: typing.Annotated[typing.Optional[str], fastapi.Query(description="Formato: cadena ISO 8601 (YYYY-MM-DDTHH:MM:SSZ)")] = None,
) -> user_schema.UserCountSchema:
    """
    Obtiene el número de usuarios que no han solicitado hipnosis según los filtros proporcionados.
    """

    # Ambas fechas deben ser provistas juntas o ninguna
    if (fromDate is None) ^ (toDate is None):
        raise fastapi.HTTPException(
            status_code=400,
            detail="fromDate y toDate deben proporcionarse juntas o no enviarse.",
        )

    # Verificamos el formato ISO de las fechas si son provistas
    if fromDate is not None and not dates_utils.verifyISOFormat(fromDate):
        raise fastapi.HTTPException(
            status_code=400,
            detail=f"La fecha fromDate proporcionada ({fromDate}) no tiene formato ISO.",
        )

    if toDate is not None and not dates_utils.verifyISOFormat(toDate):
        raise fastapi.HTTPException(
            status_code=400,
            detail=f"La fecha toDate proporcionada ({toDate}) no tiene formato ISO.",
        )

    if fromDate is not None and toDate is not None:
        fromDateTimestamp = dates_utils.convertISOtoTimestamp(fromDate)
        toDateTimestamp = dates_utils.convertISOtoTimestamp(toDate)

        if toDateTimestamp < fromDateTimestamp:
            raise fastapi.HTTPException(
                status_code=400,
                detail="toDate debe ser mayor o igual que fromDate.",
            )

    count = await users_service.getUsersWithoutHypnosisRequestCount(
        fromDate=fromDate,
        toDate=toDate,
    )

    return user_schema.UserCountSchema(count=count, fromDate=fromDate, toDate=toDate)


@ROUTER.get(
    "/distribution/portal",
    summary="Obtener distribución de usuarios por portal",
    response_class=fastapi.responses.JSONResponse,
    response_model=user_schema.UserPortalDistributionSchema,
    responses={
    200: {"description": "Respuesta exitosa", "model": user_schema.UserPortalDistributionSchema},
    400: {"description": "Solicitud inválida"},
    500: {"description": "Error interno del servidor"},
    },
)
async def getUserPortalDistribution(
    portal: typing.Annotated[str, fastapi.Query(description="Portal (userLevel) para el cual se calculará la distribución")],
    fromDate: typing.Annotated[typing.Optional[str], fastapi.Query(description="Formato: cadena ISO 8601 (YYYY-MM-DDTHH:MM:SSZ)")] = None,
    toDate: typing.Annotated[typing.Optional[str], fastapi.Query(description="Formato: cadena ISO 8601 (YYYY-MM-DDTHH:MM:SSZ)")] = None,
) -> user_schema.UserPortalDistributionSchema:
    """
    Obtiene la distribución de usuarios de un portal específico, agrupando por género y rangos de edad.
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

    if fromDate is not None and not dates_utils.verifyISOFormat(fromDate):
        raise fastapi.HTTPException(
            status_code=400,
            detail=f"La fecha fromDate proporcionada ({fromDate}) no tiene formato ISO.",
        )

    if toDate is not None and not dates_utils.verifyISOFormat(toDate):
        raise fastapi.HTTPException(
            status_code=400,
            detail=f"La fecha toDate proporcionada ({toDate}) no tiene formato ISO.",
        )

    if fromDate is not None and toDate is not None:
        fromDateTimestamp = dates_utils.convertISOtoTimestamp(fromDate)
        toDateTimestamp = dates_utils.convertISOtoTimestamp(toDate)

        if toDateTimestamp < fromDateTimestamp:
            raise fastapi.HTTPException(
                status_code=400,
                detail="toDate debe ser mayor o igual que fromDate.",
            )

    distribution = await users_service.getUserPortalDistribution(
        portal=portal,
        fromDate=fromDate,
        toDate=toDate,
    )

    return distribution