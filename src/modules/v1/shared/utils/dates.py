import datetime

def verifyISOFormat(
    dateString: str,
) -> bool:
    """
    Simple funcion para verificar si una fecha está en formato ISO.
    """
    try:
        datetime.datetime.fromisoformat(dateString)
        return True
    except ValueError:
        return False
    
def convertISOtoTimestamp(
    dateString: str,
) -> float:
    """
    Convierte una fecha en formato ISO a un timestamp.
    """
    dt = datetime.datetime.fromisoformat(dateString)
    return dt.timestamp()

def convertTimestampToISO(
    timestamp: float,
) -> str:
    """
    Convierte un timestamp a una fecha en formato ISO.
    """
    dt = datetime.datetime.fromtimestamp(timestamp)
    return dt.isoformat()

def convertISOtoDatetime(
    dateString: str,
) -> datetime.datetime:
    """
    Convierte una fecha en formato ISO a un objeto datetime.
    """
    return datetime.datetime.fromisoformat(dateString)


def parseISODatetime(
    dateString: str,
) -> datetime.datetime:
    """
    Convierte una cadena ISO 8601 (aceptando sufijo 'Z') a datetime aware.
    """

    normalized = dateString.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"

    try:
        return datetime.datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError(
            f"El valor proporcionado ({dateString}) no tiene formato ISO 8601 válido."
        ) from exc