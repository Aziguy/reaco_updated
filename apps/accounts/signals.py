from allauth.account.signals import user_signed_up
from django.core.cache import cache
from django.dispatch import receiver

from apps.core.ratelimit import client_ip

from .emails import signup_counter_key


@receiver(user_signed_up)
def on_signup(request, user, **kwargs):
    if request is None:
        return
    request.device_signup = True
    key = signup_counter_key(client_ip(request))
    if not cache.add(key, 1, 24 * 3600):
        cache.incr(key)
