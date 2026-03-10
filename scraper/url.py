"""AES URL parser — extracts event key and division ID from AES URLs."""

from __future__ import annotations

import re
from urllib.parse import urlparse


def parse_aes_url(url: str) -> tuple[str, int]:
    """Parse an AES URL and return (event_key, division_id).

    Supported formats:
        /event/{key}/division/{id}/schedule
        /event/{key}/divisions/{id}/overview
        /event/{key}/division/{id}/...
        /event/{key}/divisions/{id}/...
    """
    parsed = urlparse(url)
    path = parsed.path

    # Match /event/{key}/division(s)/{id}
    match = re.search(r"/event/([^/]+)/divisions?/(\d+)", path)
    if match:
        return match.group(1), int(match.group(2))

    raise ValueError(f"Cannot parse AES URL: {url}")
