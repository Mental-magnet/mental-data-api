import typing
import fastapi
import logging

from src.modules.v1.shared.utils import dates as dates_utils
from ..schemas import suscribers_schema
from ..services import suscribers_service

LOGGER = logging.getLogger("uvicorn").getChild("v1.users.controllers.suscribers")


ROUTER = fastapi.APIRouter(
    prefix="/suscribers",
)


@ROUTER.get(
    "/count",
    summary="Obtener todos los suscriptores",
    response_class=fastapi.responses.JSONResponse,
    response_model=suscribers_schema.SuscribersSchema,
    responses={
        200: {"description": "Respuesta exitosa", "model": suscribers_schema.SuscribersSchema},
        400: {"description": "Solicitud inválida"},
        500: {"description": "Error interno del servidor"},
    },
)
async def getSuscribers(
    isActive: typing.Annotated[bool, fastapi.Query()] = True, # Miembros activos son aquellos cuya membresía es válida al sumar un mes a la fecha actual
    fromDate: typing.Annotated[typing.Optional[str], fastapi.Query(description="Formato: cadena de fecha ISO 8601 (YYYY-MM-DDTHH:MM:SSZ)")] = None,
    toDate: typing.Annotated[typing.Optional[str], fastapi.Query(description="Formato: cadena de fecha ISO 8601 (YYYY-MM-DDTHH:MM:SSZ)")] = None,
) -> suscribers_schema.SuscribersSchema:
    """
    Obtiene el número de suscriptores según los filtros proporcionados.
    """

    # Ambas fechas deben ser provistas juntas o ninguna
    # El operador ^ es el XOR (o exclusivo)
    if (fromDate is None) ^ (toDate is None):
        raise fastapi.HTTPException(
            status_code=400,
            detail="Los parámetros fromDate y toDate deben proporcionarse juntos o no incluirse.",
        )
    
    # Verificamos el formato ISO de las fechas si son provistas
    if fromDate is not None and not dates_utils.verifyISOFormat(fromDate):
        raise fastapi.HTTPException(
            status_code=400,
            detail=f"El parámetro fromDate ({fromDate}) no tiene el formato ISO válido.",
        )

    if toDate is not None and not dates_utils.verifyISOFormat(toDate):
        raise fastapi.HTTPException(
            status_code=400,
            detail=f"El parámetro toDate ({toDate}) no tiene el formato ISO válido.",
        )

    # toDate debe ser mayor o igual a fromDate
    # comparamos usando timestamp para ser más precisos
    if fromDate is not None and toDate is not None:
        fromDateTimestamp = dates_utils.convertISOtoTimestamp(fromDate)
        toDateTimestamp = dates_utils.convertISOtoTimestamp(toDate)

        if toDateTimestamp < fromDateTimestamp:
            raise fastapi.HTTPException(
                status_code=400,
                detail="El parámetro toDate debe ser mayor o igual que fromDate.",
            )
        
    LOGGER.info(
        f"Obteniendo suscriptores con isActive={isActive}, fromDate={fromDate}, toDate={toDate}"
    )    

    count = await suscribers_service.getAllSuscribersCount(
        isActive=isActive,
        fromDate=fromDate,
        toDate=toDate,
    )

    LOGGER.info(
        f"Se encontraron {count} suscriptores con isActive={isActive}, fromDate={fromDate}, toDate={toDate}"
    )

    return suscribers_schema.SuscribersSchema(count=count, fromDate=fromDate, toDate=toDate)