import aiocache
import typing
from ..repository import USERS_REPOSITORY


@aiocache.cached_stampede(
    lease=2,
    ttl=60,
    skip_cache_func=lambda count: count == 0,
)
async def _getAllSuscribersCount(
    isActive: bool,
    fromDate: str | None,
    toDate: str | None,
) -> int:

    count = await USERS_REPOSITORY.countSuscribers(
        isActive=isActive,
        fromDate=fromDate,
        toDate=toDate,
    )

    return count

getAllSuscribersCount = typing.cast(
    typing.Callable[
        [bool, str | None, str | None], typing.Awaitable[int]
    ],
    _getAllSuscribersCount,
)
