import aiocache
import collections
import datetime
import typing
from src.modules.v1.shared.utils import dates as dates_utils
from ..repository import USERS_REPOSITORY
from ..schemas import user_schema



@aiocache.cached_stampede(
    lease=2,
    ttl=60,
    skip_cache_func=lambda count: count == 0,
)
async def _getUsersWithAURACount(
    isActive: bool,
    fromDate: str | None,
    toDate: str | None,
) -> int:

    count = await USERS_REPOSITORY.countUsersWithAURA(
        isActive=isActive,
        fromDate=fromDate,
        toDate=toDate,
    )

    return count



@aiocache.cached_stampede(
    lease=2,
    ttl=60,
)
async def _getUserByID(
    userID: str,
) -> user_schema.UserSchema | None:
    """
    Obtiene un usuario por su ID.
    """

    user = await USERS_REPOSITORY.getUserByID(userID=userID)
    return user



@aiocache.cached_stampede(
    lease=2,
    ttl=60,
    skip_cache_func=lambda userIDs: len(userIDs) == 0,
)
async def _getUsersByListOfIDs(
    userIDs: list[str],
) -> list[user_schema.UserSchema]:
    """
    Obtiene una lista de usuarios por sus IDs.
    """

    users = await USERS_REPOSITORY.getUsersByListOfIDs(userIDs=userIDs)

    return users



@aiocache.cached_stampede(
    lease=2,
    ttl=60,
    skip_cache_func=lambda count: count == 0,
)
async def _getUsersWithoutHypnosisRequestCount(
    fromDate: str | None,
    toDate: str | None,
) -> int:

    count = await USERS_REPOSITORY.countUsersWithoutHypnosisRequest(
        fromDate=fromDate,
        toDate=toDate,
    )

    return count


getUsersWithoutHypnosisRequestCount = typing.cast(
    typing.Callable[[str | None, str | None], typing.Awaitable[int]],
    _getUsersWithoutHypnosisRequestCount,
)

# Definimos los rangos de edad para la distribución
AGE_BUCKETS: tuple[tuple[str, int, int | None], ...] = (
    ("18-24", 18, 24),
    ("25-34", 25, 34),
    ("35-44", 35, 44),
    ("45-54", 45, 54),
    ("55-64", 55, 64),
    ("65+", 65, None),
)

# Edad por debajo de la cual se considera "menor de edad"
UNDERAGE_BUCKET = "0-17"


def _calculateAge(birthdate: str, reference: datetime.datetime) -> int | None:
    try:
        birthDatetime = dates_utils.parseISODatetime(birthdate)
    except ValueError:
        return None

    if birthDatetime.tzinfo is None:
        birthDatetime = birthDatetime.replace(tzinfo=datetime.timezone.utc)

    referenceUTC = reference.astimezone(datetime.timezone.utc)

    years = referenceUTC.year - birthDatetime.year
    hasHadBirthday = (
        (referenceUTC.month, referenceUTC.day)
        >= (birthDatetime.month, birthDatetime.day)
    )

    return years if hasHadBirthday else years - 1


def _resolveAgeBucket(age: int) -> str:
    if age < AGE_BUCKETS[0][1]:
        return UNDERAGE_BUCKET

    for bucketName, startAge, endAge in AGE_BUCKETS:
        if age < startAge:
            continue
        if endAge is None or age <= endAge:
            return bucketName

    return AGE_BUCKETS[-1][0]


def _buildPortalDistribution(
    portal: str,
    users: list[user_schema.UserSchema],
) -> user_schema.UserPortalDistributionSchema:
    totalUsers = len(users)

    genreCounter: collections.Counter[str] = collections.Counter()
    ageCounter: collections.Counter[str] = collections.Counter()

    referenceDate = datetime.datetime.now(datetime.timezone.utc)

    for user in users:
        if user.gender:
            genreCounter[user.gender] += 1

        age = _calculateAge(user.birthdate, referenceDate)
        if age is None or age < 0:
            continue

        bucket = _resolveAgeBucket(age)
        ageCounter[bucket] += 1

    # Ordenamos los buckets de edad para la salida
    # 0-17, 18-24, 25-34, ...
    orderedAgeBuckets: list[str] = [UNDERAGE_BUCKET] + [
        bucketName for bucketName, _, _ in AGE_BUCKETS
    ]

    ageDistribution : dict[str, int] = {}

    for bucket in orderedAgeBuckets:
        if ageCounter.get(bucket):
            ageDistribution[bucket] = ageCounter[bucket]

    genreDistribution = dict(genreCounter)

    return user_schema.UserPortalDistributionSchema(
        portal=portal,
        totalUsers=totalUsers,
        genreDistribution=genreDistribution,
        ageDistribution=ageDistribution,
    )


@aiocache.cached_stampede(
    lease=2,
    ttl=60,
    skip_cache_func=lambda distribution: distribution.totalUsers == 0,
)
async def _getUserPortalDistribution(
    portal: str,
    fromDate: str | None,
    toDate: str | None,
) -> user_schema.UserPortalDistributionSchema:

    users = await USERS_REPOSITORY.getUsersByPortal(
        portal=portal,
        fromDate=fromDate,
        toDate=toDate,
    )

    return _buildPortalDistribution(portal=portal, users=users)


getUsersWithAURACount = typing.cast(
    typing.Callable[
        [bool, str | None, str | None], typing.Awaitable[int]
    ],
    _getUsersWithAURACount,
)


getUserByID = typing.cast(
    typing.Callable[
        [str], typing.Awaitable[user_schema.UserSchema | None]
    ],
    _getUserByID,
)


getUsersByListOfIDs = typing.cast(
    typing.Callable[
        [list[str]], typing.Awaitable[list[user_schema.UserSchema]]
    ],
    _getUsersByListOfIDs,
)


getUserPortalDistribution = typing.cast(
    typing.Callable[
        [str, str | None, str | None],
        typing.Awaitable[user_schema.UserPortalDistributionSchema],
    ],
    _getUserPortalDistribution,
)
