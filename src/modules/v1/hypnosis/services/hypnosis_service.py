import aiocache
import typing

from ..repository import HYPNOSIS_REPOSITORY
from ..schemas import audiorequest_schema

CACHE_TTL_SECONDS = 5  # Keep dashboard time series highly up-to-date


@aiocache.cached_stampede(
    lease=2,
    ttl=CACHE_TTL_SECONDS,
    skip_cache_func=lambda count: count == 0,
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


@aiocache.cached_stampede(
    lease=2,
    ttl=CACHE_TTL_SECONDS,
    skip_cache_func=lambda count: count == 0,
)
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


@aiocache.cached_stampede(
    lease=2,
    ttl=CACHE_TTL_SECONDS,
)
async def _getAllHypnosisRequests(
    fromDate: int | None,
    toDate: int | None,
) -> list[audiorequest_schema.AudioRequestSchema]:

    requests = await HYPNOSIS_REPOSITORY.getAllAudioRequests(
        fromDate=fromDate,
        toDate=toDate,
    )

    return requests

@aiocache.cached_stampede(
    lease=2,
    ttl=CACHE_TTL_SECONDS,
)
async def _getHypnosisRequestByID(
    requestID: str,
) -> audiorequest_schema.AudioRequestSchema | None:

    request = await HYPNOSIS_REPOSITORY.getAudioRequestByID(requestID=requestID)

    return request


@aiocache.cached_stampede(
    lease=2,
    ttl=CACHE_TTL_SECONDS,
)
async def _getHypnosisRequestsByListOfIDs(
    requestIDs: list[str],
) -> list[audiorequest_schema.AudioRequestSchema]:

    requests = await HYPNOSIS_REPOSITORY.getAudioRequestsByListOfIDs(requestIDs=requestIDs)

    return requests


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

getAllHypnosisRequests = typing.cast(
    typing.Callable[
        [int | None, int | None],
        typing.Awaitable[list[audiorequest_schema.AudioRequestSchema]],
    ],
    _getAllHypnosisRequests,
)

getHypnosisRequestByID = typing.cast(
    typing.Callable[
        [str],
        typing.Awaitable[audiorequest_schema.AudioRequestSchema | None],
    ],
    _getHypnosisRequestByID,
)


getHypnosisRequestsByListOfIDs = typing.cast(
    typing.Callable[
        [list[str]],
        typing.Awaitable[list[audiorequest_schema.AudioRequestSchema]],
    ],
    _getHypnosisRequestsByListOfIDs,
)