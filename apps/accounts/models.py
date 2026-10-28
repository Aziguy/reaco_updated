from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from .emails import canonical


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra):
        if not email:
            raise ValueError("L'adresse email est obligatoire.")
        user = self.model(email=self.normalize_email(email), **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra):
        extra.setdefault("is_staff", False)
        extra.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra)

    def create_superuser(self, email, password=None, **extra):
        extra.update(is_staff=True, is_superuser=True)
        return self._create_user(email, password, **extra)


class User(AbstractUser):
    username = None
    email = models.EmailField("adresse email", unique=True)
    email_canonical = models.CharField(
        "adresse normalisée", max_length=254, db_index=True, blank=True, editable=False
    )

    household_size = models.PositiveSmallIntegerField(
        "personnes au foyer", default=2, validators=[MinValueValidator(1), MaxValueValidator(20)]
    )
    postal_code = models.CharField("code postal", max_length=10, blank=True)
    city = models.CharField("ville", max_length=120, blank=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    search_radius_km = models.PositiveSmallIntegerField(
        "rayon de recherche (km)",
        default=10,
        validators=[MinValueValidator(1), MaxValueValidator(100)],
    )
    expiry_reminders = models.BooleanField("rappels de péremption par email", default=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        verbose_name = "utilisateur"

    def __str__(self):
        return self.get_full_name() or self.email

    def save(self, *args, **kwargs):
        self.email_canonical = canonical(self.email)
        update_fields = kwargs.get("update_fields")
        if update_fields is not None and "email" in update_fields:
            kwargs["update_fields"] = {*update_fields, "email_canonical"}
        super().save(*args, **kwargs)

    @property
    def has_location(self) -> bool:
        return self.latitude is not None and self.longitude is not None

    @property
    def location(self):
        if not self.has_location:
            return None
        return (self.latitude, self.longitude, self.search_radius_km)


class Device(models.Model):
    """A browser identified by the hash of a signed cookie."""

    digest = models.CharField("empreinte", max_length=64, unique=True)
    created_at = models.DateTimeField("vu la première fois", auto_now_add=True)

    class Meta:
        verbose_name = "appareil"

    def __str__(self):
        return f"Appareil {self.digest[:8]}"


class DeviceLink(models.Model):
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name="links")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="device_links")
    signed_up = models.BooleanField("compte créé ici", default=False)
    first_seen = models.DateTimeField("première connexion", auto_now_add=True)
    last_seen = models.DateTimeField("dernière connexion", auto_now=True)

    class Meta:
        verbose_name = "connexion d'appareil"
        verbose_name_plural = "connexions d'appareils"
        constraints = [
            models.UniqueConstraint(fields=["device", "user"], name="unique_device_user")
        ]

    def __str__(self):
        return f"{self.user} sur {self.device}"
