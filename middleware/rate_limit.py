import time
from collections import defaultdict
from fastapi import HTTPException, status


# In-memory rate limit store: {key: [(timestamp, count)]}
_ip_buckets: dict[str, list[tuple[float, int]]] = defaultdict(list)
_user_buckets: dict[str, list[tuple[float, int]]] = defaultdict(list)


def _clean_bucket(bucket: list[tuple[float, int]], window_sec: int, now: float) -> list[tuple[float, int]]:
    cutoff = now - window_sec
    return [(ts, cnt) for ts, cnt in bucket if ts > cutoff]


def check_rate_limit(ip: str, endpoint: str, max_req: int, window_sec: int) -> bool:
    """Returns True if rate limit is NOT exceeded, False if exceeded."""
    key = f"{ip}:{endpoint}"
    now = time.time()
    bucket = _clean_bucket(_ip_buckets[key], window_sec, now)
    total = sum(cnt for _, cnt in bucket)
    if total >= max_req:
        return False
    bucket.append((now, 1))
    _ip_buckets[key] = bucket
    return True


def check_user_rate_limit(user_id: int, endpoint: str, max_req: int, window_sec: int) -> bool:
    """Returns True if rate limit is NOT exceeded, False if exceeded."""
    key = f"{user_id}:{endpoint}"
    now = time.time()
    bucket = _clean_bucket(_user_buckets[key], window_sec, now)
    total = sum(cnt for _, cnt in bucket)
    if total >= max_req:
        return False
    bucket.append((now, 1))
    _user_buckets[key] = bucket
    return True
