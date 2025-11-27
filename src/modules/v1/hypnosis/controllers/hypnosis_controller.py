import typing
import fastapi
import logging
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
    fromDate: typing.Annotated[typing.Optional[int], fastapi.Query(description="Timestamp Unix (segundos, entero)")] = None,
    toDate: typing.Annotated[typing.Optional[int], fastapi.Query(description="Timestamp Unix (segundos, entero)")] = None,
) -> audiorequest_schema.AudioRequestCountSchema:
    """
    Obtiene el número de solicitudes de audio.

    Sin rango de fechas devuelve el total histórico; con fromDate/toDate solo
    cuenta las solicitudes creadas dentro de ese intervalo.
    """

    # Ambas fechas deben ser provistas juntas o ninguna
    # El operador ^ es el XOR (o exclusivo)
    if (fromDate is None) ^ (toDate is None):
        raise fastapi.HTTPException(
            status_code=400,
            detail="Los parámetros fromDate y toDate deben proporcionarse juntos o no incluirse.",
        )
    
    if fromDate is not None and toDate is not None and toDate < fromDate:
        raise fastapi.HTTPException(
            status_code=400,
            detail="El parámetro toDate debe ser mayor o igual que fromDate.",
        )

    # Al suministrar un rango se limita el conteo a solicitudes creadas dentro de esas fechas.
    count : int = await hypnosis_service.getAllHypnosisRequestsCount(
        fromDate,
        toDate,
    )

    return audiorequest_schema.AudioRequestCountSchema(count=count , fromDate=fromDate, toDate=toDate)


@ROUTER.get(
    "/count/audio-requests/listened-status",
    summary="Obtener conteo de solicitudes de audio por estado de escucha",
    response_class=fastapi.responses.JSONResponse,
    response_model=audiorequest_schema.AudioRequestCountSchema,
    responses={
        200: {"description": "Respuesta exitosa", "model": audiorequest_schema.AudioRequestCountSchema},
        400: {"description": "Solicitud inválida"},
        500: {"description": "Error interno del servidor"},
    },
)
async def getAudioRequestsCountByListenedStatus(
    isListened: typing.Annotated[
        bool,
        fastapi.Query(
            description="Indica si se deben contar solicitudes escuchadas (True) o no escuchadas (False).",
        ),
    ] = False,
    fromDate: typing.Annotated[typing.Optional[int], fastapi.Query(description="Timestamp Unix (segundos, entero)")] = None,
    toDate: typing.Annotated[typing.Optional[int], fastapi.Query(description="Timestamp Unix (segundos, entero)")] = None,
) -> audiorequest_schema.AudioRequestCountSchema:
    """
    Obtiene el número de solicitudes de audio según su estado de escucha.

    Sin rango de fechas consulta el histórico; al indicar fromDate/toDate se
    limita a las solicitudes creadas dentro del intervalo.
    """

    # Ambas fechas deben ser provistas juntas o ninguna
    if (fromDate is None) ^ (toDate is None):
        raise fastapi.HTTPException(
            status_code=400,
            detail="Los parámetros fromDate y toDate deben proporcionarse juntos o no incluirse.",
        )

    if fromDate is not None and toDate is not None and toDate < fromDate:
        raise fastapi.HTTPException(
            status_code=400,
            detail="El parámetro toDate debe ser mayor o igual que fromDate.",
        )

    # Cuando existe un rango de fechas solo se contabilizan solicitudes creadas dentro del intervalo.
    count: int = await hypnosis_service.getHypnosisRequestsCountByListenedStatus(
        isListened,
        fromDate,
        toDate,
    )

    return audiorequest_schema.AudioRequestCountSchema(
        count=count,
        fromDate=fromDate,
        toDate=toDate,
        isListened=isListened,
    )