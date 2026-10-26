"""Conservative, dependency-free SCIENCE chronology parsing."""
import re
from datetime import datetime


def strict_iso_day(value):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def registry_publication_day(value):
    """Unknown or malformed registry publication dates remain unknown."""
    return strict_iso_day(value)

def source_eligible_at_cutoff(published_at, verified_at, cutoff):
    """Only independently dated source evidence can clear this preliminary gate.

    This is a chronology check, not certification of source authenticity.
    """
    publication = strict_iso_day(published_at)
    verification = strict_iso_day(verified_at)
    limit = strict_iso_day(cutoff)
    return bool(publication and verification and limit and
                publication <= limit and verification <= limit)
