from django.conf import settings
from django.core.cache import cache

TEAM_ANALYTICS_KEY_PREFIX = "team_analytics"
COMPANY_METRICS_KEY = "company_metrics"


def _ttl():
    return getattr(settings, "ANALYTICS_CACHE_TTL", 300)


def team_analytics_cache_key(team_id):
    return f"{TEAM_ANALYTICS_KEY_PREFIX}:{team_id}"


def get_cached_team_analytics(team_id):
    return cache.get(team_analytics_cache_key(team_id))


def set_cached_team_analytics(team_id, data):
    cache.set(team_analytics_cache_key(team_id), data, _ttl())


def invalidate_team_analytics(team_id):
    cache.delete(team_analytics_cache_key(team_id))


def get_cached_company_metrics():
    return cache.get(COMPANY_METRICS_KEY)


def set_cached_company_metrics(data):
    cache.set(COMPANY_METRICS_KEY, data, _ttl())


def invalidate_company_metrics():
    cache.delete(COMPANY_METRICS_KEY)


def invalidate_analytics_cache_for_submission(submission):
    team_id = getattr(submission.user, "team_id", None)
    if team_id:
        invalidate_team_analytics(team_id)
    invalidate_company_metrics()
