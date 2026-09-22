from celery import shared_task
from django.core.cache import cache

from .services import refresh_live_results_for_all


@shared_task
def refresh_live_benchmark_results():
    """Refresh live benchmark snapshots from the current source-module data."""
    lock_key = "benchmarking:live-refresh-lock"
    if not cache.add(lock_key, "locked", timeout=55 * 60):
        return "Live benchmark refresh already running."
    try:
        refresh_live_results_for_all()
    finally:
        cache.delete(lock_key)
    return "Live benchmark results refreshed."
