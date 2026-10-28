import hashlib
import secrets

from django.db.models import Q

from .models import Device, DeviceLink, User

COOKIE = "cg_device"
SALT = "accounts.device"
MAX_AGE = 2 * 365 * 24 * 3600


def new_token() -> str:
    return secrets.token_urlsafe(24)


def digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def link(user, token_digest: str, *, signed_up: bool = False) -> DeviceLink:
    device, _ = Device.objects.get_or_create(digest=token_digest)
    item, created = DeviceLink.objects.get_or_create(
        device=device, user=user, defaults={"signed_up": signed_up}
    )
    if not created:
        item.save(update_fields=["last_seen"])
    return item


def linked_users(user):
    """Other accounts that signed in on one of this user's devices."""
    devices = DeviceLink.objects.filter(user=user).values("device")
    return User.objects.filter(device_links__device__in=devices).exclude(pk=user.pk).distinct()


def free_siblings(user) -> list[int]:
    """This user and the accounts without a current subscription sharing a device with it."""
    from apps.billing.models import Subscription

    paying = Subscription.objects.current().values("user")
    others = linked_users(user).filter(~Q(pk__in=paying), is_staff=False)
    return [user.pk, *others.values_list("pk", flat=True)]
