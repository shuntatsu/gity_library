from functools import wraps
from django.http import HttpResponse
from django.core.cache import cache

def is_superuser(user):
    return user.is_authenticated and user.is_superuser

def rate_limit(rate, per):
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            key = f'{func.__name__}:{request.META["REMOTE_ADDR"]}'
            count = cache.get(key, 0)
            if count >= rate:
                return HttpResponse("Too Many Requests", status=429)
            cache.set(key, count + 1, per)
            return func(request, *args, **kwargs)
        return wrapper
    return decorator
