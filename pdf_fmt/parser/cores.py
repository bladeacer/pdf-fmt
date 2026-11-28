"""Core count selection."""

import os
from typing import Any, Dict


def _get_validated_cores(config: Dict[str, Any]) -> int:
    """Calculates and validates the number of CPU cores to use."""
    available = os.cpu_count() or 1
    max_cores = max(1, available - 1)
    cores = config.get("processing", {}).get("cores", max_cores)
    try:
        cores_int = int(cores)
        if 0 < cores_int < available:
            return cores_int
    except (ValueError, TypeError):
        pass
    return max_cores
