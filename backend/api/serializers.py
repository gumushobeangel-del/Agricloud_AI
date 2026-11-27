from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.utils import timezone
from rest_framework import serializers

from .models import Crop, CropYieldBenchmark, Farm, FarmQuestion, HarvestRecord, MarketPrice, Notification, Recommendation

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    profile_image = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ("id", "username", "email", "first_name", "last_name", "role", "district", "phone", "profile_image")
        read_only_fields = ("id", "role")

    def get_profile_image(self, user):
        return user.profile_image.url if user.profile_image else None

class ProfileImageUploadSerializer(serializers.Serializer):
    profile_image = serializers.ImageField()

    def validate_profile_image(self, value):
        if value.size > 5 * 1024 * 1024:
            raise serializers.ValidationError("Profile pictures must be 5 MB or smaller.")
        if getattr(value.image, "format", None) not in {"JPEG", "PNG", "WEBP"}:
            raise serializers.ValidationError("Upload a valid JPEG, PNG, or WebP image.")
        return value


class CropDiseaseImageSerializer(serializers.Serializer):
    image = serializers.ImageField()

    def validate_image(self, value):
        if value.size > 5 * 1024 * 1024:
            raise serializers.ValidationError("Crop images must be 5 MB or smaller.")
        if getattr(value.image, "format", None) not in {"JPEG", "PNG", "WEBP"}:
            raise serializers.ValidationError("Upload a valid JPEG, PNG, or WebP image.")
        return value


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=10)

    class Meta:
        model = User
        fields = ("username", "email", "password", "first_name", "last_name", "district", "phone")

    def validate_password(self, value):
        validate_password(value)
        return value

    def create(self, validated_data):
        return User.objects.create_user(**validated_data, role=User.Role.FARMER)


class FarmSerializer(serializers.ModelSerializer):
    owner_name = serializers.CharField(source="owner.get_full_name", read_only=True)

    class Meta:
        model = Farm
        fields = (
            "id", "owner", "owner_name", "name", "district", "crop", "size_hectares",
            "latitude", "longitude", "soil_type", "created_at", "updated_at",
        )
        read_only_fields = ("id", "owner", "owner_name", "created_at", "updated_at")

    def validate_latitude(self, value):
        if not -90 <= value <= 90:
            raise serializers.ValidationError("Latitude must be between -90 and 90.")
        return value

    def validate_longitude(self, value):
        if not -180 <= value <= 180:
            raise serializers.ValidationError("Longitude must be between -180 and 180.")
        return value

    def validate_size_hectares(self, value):
        if value <= 0 or value > 1_000_000:
            raise serializers.ValidationError("Farm size must be greater than zero and at most 1,000,000 hectares.")
        return value


class CropSerializer(serializers.ModelSerializer):
    class Meta:
        model = Crop
        fields = ("id", "name", "local_names", "category", "guidance_notes", "source_title", "source_url", "verified", "active")

    def validate(self, attrs):
        verified = attrs.get("verified", getattr(self.instance, "verified", False))
        source_title = attrs.get("source_title", getattr(self.instance, "source_title", ""))
        source_url = attrs.get("source_url", getattr(self.instance, "source_url", ""))
        if verified and (not source_title or not source_url):
            raise serializers.ValidationError("Verified crop records require a source title and URL.")
        return attrs


class RecommendationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recommendation
        fields = ("id", "farm", "crop", "planting_date", "guidance", "basis", "risks", "created_at")
        read_only_fields = ("id", "guidance", "basis", "risks", "created_at")


class HarvestRecordSerializer(serializers.ModelSerializer):
    farm_name = serializers.CharField(source="farm.name", read_only=True)
    recorded_by = serializers.PrimaryKeyRelatedField(read_only=True)
    class Meta:
        model = HarvestRecord
        fields = ("id", "farm", "farm_name", "crop", "harvest_date", "quantity_kg", "recorded_by", "created_at")
        read_only_fields = ("id", "farm_name", "recorded_by", "created_at")

    def validate_crop(self, value):
        if not value.strip() or len(value.strip()) > 100:
            raise serializers.ValidationError("Provide a crop name up to 100 characters.")
        return value.strip()

    def validate_quantity_kg(self, value):
        if value <= 0:
            raise serializers.ValidationError("Harvest quantity must be greater than zero.")
        return value

    def validate_harvest_date(self, value):
        if value > timezone.localdate():
            raise serializers.ValidationError("Harvest date cannot be in the future.")
        return value


class CropYieldBenchmarkSerializer(serializers.ModelSerializer):
    class Meta:
        model = CropYieldBenchmark
        fields = ("id", "crop", "district", "reference_year", "yield_kg_per_hectare", "source_title", "source_url")
        read_only_fields = ("id",)

    def validate_reference_year(self, value):
        if value > timezone.localdate().year:
            raise serializers.ValidationError("Reference year cannot be in the future.")
        return value

    def validate_yield_kg_per_hectare(self, value):
        if value <= 0:
            raise serializers.ValidationError("Reference yield must be greater than zero.")
        return value

    def validate(self, attrs):
        if not (attrs.get("source_title", getattr(self.instance, "source_title", "")) or "").strip():
            raise serializers.ValidationError({"source_title": "A source title is required."})
        if not (attrs.get("source_url", getattr(self.instance, "source_url", "")) or "").strip():
            raise serializers.ValidationError({"source_url": "A source URL is required."})
        return attrs


class MarketPriceSerializer(serializers.ModelSerializer):
    class Meta:
        model = MarketPrice
        fields = (
            "id", "commodity", "market", "district", "price", "unit", "currency",
            "observed_at", "source_title", "source_url",
        )

    def validate_price(self, value):
        if value <= 0:
            raise serializers.ValidationError("Price must be greater than zero.")
        return value

    def validate_observed_at(self, value):
        if value > timezone.localdate():
            raise serializers.ValidationError("Observation date cannot be in the future.")
        return value


class FarmQuestionSerializer(serializers.ModelSerializer):
    farm_name = serializers.CharField(source="farm.name", read_only=True)
    district = serializers.CharField(source="farm.district", read_only=True)
    asked_by_name = serializers.CharField(source="asked_by.get_full_name", read_only=True)
    answered_by_name = serializers.CharField(source="answered_by.get_full_name", read_only=True)

    class Meta:
        model = FarmQuestion
        fields = (
            "id", "farm", "farm_name", "district", "asked_by", "asked_by_name",
            "question", "answer", "status", "answered_by_name", "created_at", "answered_at",
        )
        read_only_fields = ("id", "asked_by", "answer", "status", "answered_by_name", "created_at", "answered_at")

    def validate_question(self, value):
        if not value.strip():
            raise serializers.ValidationError("Question cannot be blank.")
        return value.strip()


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ("id", "farm", "title", "message", "level", "read_at", "created_at")
