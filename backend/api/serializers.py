from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import Crop, Farm, FarmQuestion, Notification, Recommendation

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username", "email", "first_name", "last_name", "role", "district", "phone")
        read_only_fields = ("id", "role")


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
