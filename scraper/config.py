AES_API_BASE = "https://results.advancedeventsystems.com/api"

# HTTP settings
REQUEST_TIMEOUT_SECONDS = 30
RATE_LIMIT_DELAY_SECONDS = 0.15
MAX_RETRIES = 3
BACKOFF_BASE_SECONDS = 2.0

# Headers
DEFAULT_HEADERS = {
    "Accept": "application/json",
    "User-Agent": "TitanSchedule/0.1.0 (tournament visualization tool)",
}
