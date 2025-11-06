import typing
import fastapi
import logging

from src.modules.v1.shared.utils import dates as dates_utils
from ..schemas import audiorequest_schema
from ..services import hypnosis_service

LOGGER = logging.getLogger("uvicorn").getChild("v1.hypnosis.controllers.hypnosis")


ROUTER = fastapi.APIRouter()



@ROUTER.get(
    "/count/audio-requests",
    summary="Obtener conteo de solicitudes de audio",
    response_class=fastapi.responses.JSONResponse,
    response_model=audiorequest_schema.AudioRequestCountSchema,
    responses={
        200: {"description": "Respuesta exitosa", "model": audiorequest_schema.AudioRequestCountSchema},
        400: {"description": "Solicitud inválida"},
        500: {"description": "Error interno del servidor"},
    },
)
async def getAudioRequestsCount(
    fromDate: typing.Annotated[typing.Optional[str], fastapi.Query(description="Formato: cadena de fecha ISO 8601 (YYYY-MM-DDTHH:MM:SSZ)")] = None,
    toDate: typing.Annotated[typing.Optional[str], fastapi.Query(description="Formato: cadena de fecha ISO 8601 (YYYY-MM-DDTHH:MM:SSZ)")] = None,
) -> audiorequest_schema.AudioRequestCountSchema:
    """
    Obtiene el número de solicitudes de audio según los filtros proporcionados.
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

    count : int = await hypnosis_service.getAllHypnosisRequestsCount(
        fromDate=fromDate,
        toDate=toDate,
    )

    return audiorequest_schema.AudioRequestCountSchema(count=count , fromDate=fromDate, toDate=toDate)


@ROUTER.get(
    "/count/audio-requests/not-listened",
    summary="Obtener conteo de solicitudes de audio no escuchadas",
    response_class=fastapi.responses.JSONResponse,
    response_model=audiorequest_schema.AudioRequestCountSchema,
    responses={
        200: {"description": "Respuesta exitosa", "model": audiorequest_schema.AudioRequestCountSchema},
        400: {"description": "Solicitud inválida"},
        500: {"description": "Error interno del servidor"},
    },
)
async def getNotListenedAudioRequestsCount(
    fromDate: typing.Annotated[typing.Optional[str], fastapi.Query()] = None,
    toDate: typing.Annotated[typing.Optional[str], fastapi.Query()] = None,
) -> audiorequest_schema.AudioRequestCountSchema:
    """
    Obtiene el número de solicitudes de audio marcadas como no escuchadas (isAvailable=True).
    """

    # Ambas fechas deben ser provistas juntas o ninguna
    if (fromDate is None) ^ (toDate is None):
        raise fastapi.HTTPException(
            status_code=400,
            detail="Los parámetros fromDate y toDate deben proporcionarse juntos o no incluirse.",
        )

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

    if fromDate is not None and toDate is not None:
        fromDateTimestamp = dates_utils.convertISOtoTimestamp(fromDate)
        toDateTimestamp = dates_utils.convertISOtoTimestamp(toDate)

        if toDateTimestamp < fromDateTimestamp:
            raise fastapi.HTTPException(
                status_code=400,
                detail="El parámetro toDate debe ser mayor o igual que fromDate.",
            )

    count: int = await hypnosis_service.getNotListenedHypnosisRequestsCount(
        fromDate=fromDate,
        toDate=toDate,
    )

    return audiorequest_schema.AudioRequestCountSchema(count=count, fromDate=fromDate, toDate=toDate)