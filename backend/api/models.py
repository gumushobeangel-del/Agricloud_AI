from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        FARMER = "farmer", "Farmer"
        EXTENSION = "extension", "Extension worker"
        ADMIN = "admin", "Administrator"

    role = models.CharField(max_length=16, choices=Role.choices, default=Role.FARMER)
    district = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=30, blank=True)

    def save(self, *args, **kwargs):
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
