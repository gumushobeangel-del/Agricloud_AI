from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class User(AbstractUser):
    class Role(models.TextChoices):
        FARMER = "farmer", "Farmer"
        EXTENSION = "extension", "Extension worker"
        ADMIN = "admin", "Administrator"

    role = models.CharField(max_length=16, choices=Role.choices, default=Role.FARMER)
    district = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    profile_image = models.ImageField(upload_to="profile-pictures/", blank=True, null=True)

    def save(self, *args, **kwargs):
        if self.is_superuser:
            self.role = self.Role.ADMIN
        self.is_staff = self.role == self.Role.ADMIN or self.is_superuser
        super().save(*args, **kwargs)


class Farm(models.Model):
    class Soil(models.TextChoices):
        UNKNOWN = "unknown", "Not specified"
        CLAY = "clay", "Clay"
        LOAM = "loam", "Loam"
        SANDY = "sandy", "Sandy"
        VOLCANIC = "volcanic", "Volcanic"

    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="farms")
    name = models.CharField(max_length=120)
    district = models.CharField(max_length=100)
    crop = models.CharField(max_length=100, blank=True)
    size_hectares = models.DecimalField(max_digits=9, decimal_places=2)
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    soil_type = models.CharField(max_length=16, choices=Soil.choices, default=Soil.UNKNOWN)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Crop(models.Model):
    name = models.CharField(max_length=100, unique=True)
    local_names = models.CharField(max_length=200, blank=True)
    category = models.CharField(max_length=80, blank=True)
    guidance_notes = models.TextField(blank=True)
    source_title = models.CharField(max_length=200, blank=True)
    source_url = models.URLField(blank=True)
    verified = models.BooleanField(default=False)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def clean(self):
        if self.verified and (not self.source_title or not self.source_url):
            raise ValidationError("Verified crops must include a source title and URL.")

    def __str__(self):
        return self.name


class CropYieldBenchmark(models.Model):
    crop = models.CharField(max_length=100)
    district = models.CharField(max_length=100, blank=True, help_text="Leave blank for a national reference.")
    reference_year = models.PositiveSmallIntegerField()
    yield_kg_per_hectare = models.DecimalField(max_digits=12, decimal_places=2)
    source_title = models.CharField(max_length=200)
    source_url = models.URLField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["crop", "district", "-reference_year"]
        constraints = [
            models.UniqueConstraint(
                fields=["crop", "district", "reference_year"],
                name="unique_crop_yield_benchmark_period",
            ),
        ]

    def clean(self):
        if self.yield_kg_per_hectare is not None and self.yield_kg_per_hectare <= 0:
            raise ValidationError({"yield_kg_per_hectare": "Reference yield must be greater than zero."})
        if self.reference_year is not None and self.reference_year > timezone.localdate().year:
            raise ValidationError({"reference_year": "Reference year cannot be in the future."})

    def __str__(self):
        return f"{self.crop} · {self.district or 'National'} · {self.reference_year}"


class HarvestRecord(models.Model):
    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name="harvest_records")
    crop = models.CharField(max_length=100)
    harvest_date = models.DateField()
    quantity_kg = models.DecimalField(max_digits=12, decimal_places=2)
    recorded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="harvest_records",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-harvest_date", "-created_at"]

    def clean(self):
        if self.quantity_kg is not None and self.quantity_kg <= 0:
            raise ValidationError({"quantity_kg": "Harvest quantity must be greater than zero."})
        if self.harvest_date is not None and self.harvest_date > timezone.localdate():
            raise ValidationError({"harvest_date": "Harvest date cannot be in the future."})

    def __str__(self):
        return f"{self.farm.name} · {self.crop} · {self.harvest_date}"


class MarketPrice(models.Model):
    commodity = models.CharField(max_length=100)
    market = models.CharField(max_length=120)
    district = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=14, decimal_places=2)
    unit = models.CharField(max_length=40, default="kg")
    currency = models.CharField(max_length=3, default="UGX")
    observed_at = models.DateField()
    source_title = models.CharField(max_length=200)
    source_url = models.URLField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-observed_at", "commodity", "market"]

    def clean(self):
        if self.price is not None and self.price <= 0:
            raise ValidationError({"price": "Market price must be greater than zero."})
        if self.observed_at is not None and self.observed_at > timezone.localdate():
            raise ValidationError({"observed_at": "Market observation date cannot be in the future."})

    def __str__(self):
        return f"{self.commodity} · {self.market} · {self.observed_at}"


class Recommendation(models.Model):
    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name="recommendations")
    crop = models.CharField(max_length=100)
    planting_date = models.DateField(null=True, blank=True)
    guidance = models.TextField()
    basis = models.JSONField(default=list)
    risks = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class FarmQuestion(models.Model):
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        RESPONDED = "responded", "Responded"

    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name="questions")
    asked_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="farm_questions")
    question = models.TextField(max_length=2000)
    answer = models.TextField(max_length=4000, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.OPEN)
    answered_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="answered_farm_questions")
    created_at = models.DateTimeField(auto_now_add=True)
    answered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["status", "-created_at"]


class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")
    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, null=True, blank=True)
    title = models.CharField(max_length=160)
    message = models.TextField()
    level = models.CharField(max_length=16, default="info")
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
