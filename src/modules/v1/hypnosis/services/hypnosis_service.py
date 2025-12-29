import typing

from ..repository import HYPNOSIS_REPOSITORY

CACHE_TTL_SECONDS = (
    60  # Optimizamos a 1 minuto para proteger la DB manteniendo datos actualizados
)


async def _getAllHypnosisRequestsCount(
    fromDate: int | None,
    toDate: int | None,
) -> int:
    count = await HYPNOSIS_REPOSITORY.countAudioRequests(
        fromDate=fromDate,
        toDate=toDate,
    )

    return count


async def _getHypnosisRequestsCountByListenedStatus(
    isListened: bool,
    fromDate: int | None,
    toDate: int | None,
) -> int:
    count = await HYPNOSIS_REPOSITORY.countAudioRequestsByListenedStatus(
        isListened=isListened,
        fromDate=fromDate,
        toDate=toDate,
    )

    return count


getAllHypnosisRequestsCount = typing.cast(
    typing.Callable[
        [int | None, int | None],
        typing.Awaitable[int],
    ],
    _getAllHypnosisRequestsCount,
)

getHypnosisRequestsCountByListenedStatus = typing.cast(
    typing.Callable[[bool, int | None, int | None], typing.Awaitable[int]],
    _getHypnosisRequestsCountByListenedStatus,
)
