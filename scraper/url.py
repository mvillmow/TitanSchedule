import re
from dataclasses import dataclass


@dataclass(frozen=True)
class AESUrlParts:
    event_key: str
    division_id: int
    pool_id: int | None


_AES_URL_RE = re.compile(
    r"/event/(?P<event_key>[A-Za-z0-9+/=]+)"
    r"/divisions/(?P<division_id>\d+)"
    r"(?:/\w+)?"
    r"(?:/pool/(?P<pool_id>-?\d+))?"
)


def parse_aes_url(url: str) -> AESUrlParts:
    """
    Parse any AES results URL into its components.

    Accepted URL patterns:
      /event/{eventKey}/divisions/{divisionId}/overview
      /event/{eventKey}/divisions/{divisionId}/overview/pool/{poolId}
      /event/{eventKey}/divisions/{divisionId}/standings
      /event/{eventKey}/divisions/{divisionId}/teams

    Raises ValueError if URL doesn't match expected AES pattern.
    """
    match = _AES_URL_RE.search(url)
    if not match:
        raise ValueError(f"URL does not match expected AES pattern: {url}")

    pool_id_str = match.group("pool_id")
    return AESUrlParts(
        event_key=match.group("event_key"),
        division_id=int(match.group("division_id")),
        pool_id=int(pool_id_str) if pool_id_str is not None else None,
    )
