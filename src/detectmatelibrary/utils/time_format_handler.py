import re
from datetime import datetime, timezone


class TimeFormatHandler:
    """A class to handle various time format parsing and conversion operations.

    This class provides methods to parse different timestamp formats and
    convert them to Unix timestamps. It includes caching for improved
    performance on repeated parsing operations.
    """

    # A conservative list of common timestamp formats we want to try when auto-detecting.
    COMMON_TIME_FORMATS = [
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S,%f",
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%d %H:%M:%S",
        "%Y/%m/%d %H:%M:%S",
        "%d/%b/%Y:%H:%M:%S %z",  # Apache style: 10/Oct/2000:13:55:36 -0700
        "%b %d %H:%M:%S",  # syslog without year
        "%H:%M:%S",
    ]

    def __init__(self) -> None:
        """Initialize the TimeFormatHandler with an empty format cache."""
        self._format_cache: dict[str, str] = {}

    def _to_unix(self, dt: datetime) -> str:
        """Convert datetime to unix timestamp string."""
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return str(int(dt.timestamp()))

    def _parse_with_format(self, time_str: str, fmt: str) -> str | None:
        """Parse time string with given format and return unix timestamp."""
        try:
            # handle syslog-like formats that lack a year by prepending the current year
            if fmt == "%b %d %H:%M:%S" and re.match(r"^[A-Za-z]{3} \d{1,2} ", time_str):
                year = datetime.now().year
                dt = datetime.strptime(f"{year} {time_str}", f"%Y {fmt}")
            else:
                dt = datetime.strptime(time_str, fmt)
            self._format_cache["last_format"] = fmt
            return self._to_unix(dt)
        except ValueError:
            return None

    def parse_timestamp(self, time_str: str, time_format: str | None = None) -> str:
        """Convert time_str to a unix timestamp string (seconds since epoch).

        If time_format is provided, try that first. Otherwise, attempt a series
        of heuristics and common formats to auto-detect the timestamp. If nothing
        matches, return "0".
        Implements a cache to speed up repeated parsing of similar formats.

        Args:
            time_str: The timestamp string to parse
            time_format: Optional explicit format string to use

        Returns:
            Unix timestamp as string, or "0" if parsing fails
        """
        if not time_str:
            return "0"

        cache_key = "last_format"

        # 1) Try cached format (if no explicit format requested)
        if not time_format:
            cached_format = self._format_cache.get(cache_key)
            if cached_format:
                ts = self._parse_with_format(time_str, cached_format)
                if ts is not None:
                    return ts

        # 2) Try caller-provided explicit format
        if time_format:
            ts = self._parse_with_format(time_str, time_format)
            if ts is not None:
                return ts

        # 3) Numeric epoch (seconds or milliseconds)
        if re.fullmatch(r"\d+(?:\.\d+)?", time_str):
            try:
                if "." in time_str:
                    val = float(time_str)
                    # if value looks like milliseconds (very large), normalize
                    if val > 1e12:
                        val /= 1000.0
                    return str(int(val))
                else:
                    ival = int(time_str)
                    # heuristic: length >= 13 -> treat as milliseconds
                    if len(time_str) >= 13:
                        ival //= 1000
                    return str(ival)
            except (ValueError, OverflowError):
                pass

        # 4) Try ISO-style parse with fromisoformat (handle trailing Z)
        try:
            iso_str = time_str[:-1] + "+00:00" if time_str.endswith("Z") else time_str
            dt = datetime.fromisoformat(iso_str)
            return self._to_unix(dt)
        except (ValueError, TypeError):
            pass

        # 5) Try the list of common formats
        for fmt in self.COMMON_TIME_FORMATS:
            ts = self._parse_with_format(time_str, fmt)
            if ts is not None:
                return ts

        # 6) Nothing matched
        return "0"

    def clear_cache(self) -> None:
        """Clear the format cache."""
        self._format_cache.clear()
