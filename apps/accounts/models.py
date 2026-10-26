from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


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

    @property
    def has_location(self) -> bool:
        return self.latitude is not None and self.longitude is not None

    @property
    def location(self):
        if not self.has_location:
            return None
        return (self.latitude, self.longitude, self.search_radius_km)
