from disposable_email_domains import blocklist
from django.conf import settings
from django.core.cache import cache

GMAIL = {"gmail.com", "googlemail.com"}


def canonical(email: str) -> str:
    """One key per mailbox: lowercase, no +tag, no dots for Gmail."""
    local, _, domain = email.strip().lower().rpartition("@")
    local = local.split("+", 1)[0]
    if domain in GMAIL:
        local, domain = local.replace(".", ""), "gmail.com"
    return f"{local}@{domain}"


def is_disposable(email: str) -> bool:
    domain = email.strip().lower().rpartition("@")[2]
    extra = {d.lower() for d in settings.BLOCKED_EMAIL_DOMAINS}
    parts = domain.split(".")
    suffixes = {".".join(parts[i:]) for i in range(len(parts) - 1)}
    return any(s in blocklist or s in extra for s in suffixes)


def signup_counter_key(ip: str) -> str:
    return f"accounts:signups:{ip}"


def signups_from(ip: str) -> int:
    return cache.get(signup_counter_key(ip), 0)


def email_verified(user) -> bool:
    """False while the sign-in address waits for its confirmation link."""
    from allauth.account.models import EmailAddress

    return not EmailAddress.objects.filter(
        user=user, email__iexact=user.email, verified=False
    ).exists()
