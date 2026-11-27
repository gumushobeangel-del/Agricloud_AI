from datetime import date, timedelta
import base64
import json
import math
import requests
from PIL import Image

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import Count, Q, Sum
from django.utils import timezone
from rest_framework import generics, permissions, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from inference_sdk import InferenceHTTPClient
from inference_sdk.http.errors import HTTPClientError as InferenceHTTPClientError

from .models import Crop, CropYieldBenchmark, Farm, FarmQuestion, HarvestRecord, MarketPrice, Notification, Recommendation
from .permissions import CanAccessFarm, CanAccessQuestion, CanManageCrop
from .serializers import (
    CropDiseaseImageSerializer,
    CropSerializer,
    CropYieldBenchmarkSerializer,
    FarmQuestionSerializer,
    FarmSerializer,
    HarvestRecordSerializer,
    MarketPriceSerializer,
    NotificationSerializer,
    ProfileImageUploadSerializer,
    RecommendationSerializer,
    RegisterSerializer,
    UserSerializer,
)
from .services.nasa_power import WeatherServiceError, fetch_daily_weather
from .services.open_meteo import fetch_current_weather
from .services.agriculture_knowledge import retrieve_knowledge
from .services.recommendations import build_planting_advice
from .services.risks import identify_climate_risks
from .services.irrigation import STAGE_COEFFICIENTS, build_irrigation_plan
from .services.market_prices import MarketDataError, SOURCE_TITLE, fetch_wfp_prices

User = get_user_model()


def can_review_all(user):
    return user.role in {User.Role.EXTENSION, User.Role.ADMIN} or user.is_staff


def _confidence_pct(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("Invalid confidence.")
    try:
        numeric_value = float(value)
    except (OverflowError, TypeError, ValueError) as exc:
        raise ValueError("Invalid confidence.") from exc
    if not math.isfinite(numeric_value) or not 0 <= numeric_value <= 100:
        raise ValueError("Confidence is outside the expected range.")
    return round(numeric_value, 1)


def _roboflow_prediction(payload):
    if not isinstance(payload, dict):
        raise ValueError("Invalid classifier response.")
    predictions = payload.get("predictions")
    if isinstance(predictions, dict):
        scores = {
            label: score for label, score in predictions.items()
            if isinstance(label, str)
            and label.strip()
            and isinstance(score, (int, float))
            and not isinstance(score, bool)
            and 0 <= score <= 1
            and math.isfinite(float(score))
        }
        if not scores:
            raise ValueError("The classifier returned no usable classes.")
        label = payload.get("top")
        if not isinstance(label, str) or label not in scores:
            label = max(scores, key=scores.get)
        confidence = scores[label]
    elif isinstance(predictions, list):
        candidates = [
            item for item in predictions
            if isinstance(item, dict)
            and isinstance(item.get("class") or item.get("class_name"), str)
            and isinstance(item.get("confidence"), (int, float))
            and not isinstance(item.get("confidence"), bool)
            and 0 <= item["confidence"] <= 1
            and math.isfinite(float(item["confidence"]))
        ]
        if not candidates:
            raise ValueError("The classifier returned no usable predictions.")
        prediction = max(candidates, key=lambda item: item["confidence"])
        label = (prediction.get("class") or prediction.get("class_name")).strip()
        confidence = prediction["confidence"]
    else:
        raise ValueError("The classifier returned no predictions.")
    if not label.strip():
        raise ValueError("The classifier returned an empty class.")
    return label.strip(), _confidence_pct(confidence * 100)


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]


class AdminOverviewView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if request.user.role != User.Role.ADMIN:
            raise PermissionDenied("Administrator access is required.")
        return Response({
            "users": User.objects.count(),
            "farmers": User.objects.filter(role=User.Role.FARMER).count(),
            "extension_workers": User.objects.filter(role=User.Role.EXTENSION).count(),
            "farms": Farm.objects.count(),
            "open_questions": FarmQuestion.objects.filter(status=FarmQuestion.Status.OPEN).count(),
            "active_crops": Crop.objects.filter(active=True).count(),
            "verified_crops": Crop.objects.filter(active=True, verified=True).count(),
            "market_records": MarketPrice.objects.count(),
        })


class AdminUsersView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def _require_admin(self, request):
        if request.user.role != User.Role.ADMIN:
            raise PermissionDenied("Administrator access is required.")

    def get(self, request):
        self._require_admin(request)
        users = User.objects.all().order_by("-date_joined")
        return Response([{
            **UserSerializer(user).data,
            "is_active": user.is_active,
            "date_joined": user.date_joined,
        } for user in users])

    def patch(self, request, user_id):
        self._require_admin(request)
        try:
            target = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        role = request.data.get("role", target.role)
        is_active = request.data.get("is_active", target.is_active)
        valid_roles = {choice for choice, _label in User.Role.choices}
        if not isinstance(role, str) or role not in valid_roles:
            raise ValidationError({"role": "Choose a valid account role."})
        if not isinstance(is_active, bool):
            raise ValidationError({"is_active": "This value must be true or false."})
        if target.pk == request.user.pk and (role != User.Role.ADMIN or not is_active):
            raise ValidationError({"detail": "You cannot remove your own administrator access."})
        if target.role == User.Role.ADMIN and (role != User.Role.ADMIN or not is_active):
            remaining_admins = User.objects.filter(role=User.Role.ADMIN, is_active=True).exclude(pk=target.pk).count()
            if remaining_admins == 0:
                raise ValidationError({"detail": "At least one active administrator must remain."})

        target.role = role
        target.is_active = is_active
        target.save(update_fields=["role", "is_active", "is_staff"])
        return Response({
            **UserSerializer(target).data,
            "is_active": target.is_active,
            "date_joined": target.date_joined,
        })

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(user)
        return Response({
            "user": UserSerializer(user).data,
            "refresh": str(refresh),
            "access": str(refresh.access_token),
        }, status=status.HTTP_201_CREATED)


class MeView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user


class ProfileImageView(APIView):
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        serializer = ProfileImageUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user
        previous_image_name = user.profile_image.name if user.profile_image else ""
        user.profile_image = serializer.validated_data["profile_image"]
        user.save(update_fields=["profile_image"])
        if previous_image_name and previous_image_name != user.profile_image.name:
            user.profile_image.storage.delete(previous_image_name)
        return Response(UserSerializer(user, context={"request": request}).data)

    def delete(self, request):
        if request.user.profile_image:
            request.user.profile_image.delete(save=True)
        return Response(UserSerializer(request.user, context={"request": request}).data)


class CropDiseaseView(APIView):
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        crop = request.data.get("crop")
        if not isinstance(crop, str) or not crop.strip() or len(crop.strip()) > 100:
            return Response({"crop": "Provide a crop name up to 100 characters."}, status=status.HTTP_400_BAD_REQUEST)
        if not settings.CROP_VISION_ENABLED:
            return Response({"detail": "Crop image analysis is disabled by the service operator."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        provider = settings.CROP_VISION_PROVIDER
        if provider == "roboflow":
            configured = (
                bool(settings.CROP_VISION_API_KEY)
                and bool(settings.CROP_VISION_MODEL)
                and settings.CROP_VISION_API_URL.lower().startswith("https://")
            )
        elif provider == "openai-compatible":
            configured = (
                bool(settings.CROP_VISION_API_KEY)
                and bool(settings.CROP_VISION_MODEL)
                and settings.LLM_API_BASE_URL.lower().startswith("https://")
            )
        else:
            configured = False
        if not configured:
            return Response(
                {"detail": "Crop image analysis requires a supported HTTPS vision provider, API key, and model."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        serializer = CropDiseaseImageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        image = serializer.validated_data["image"]
        try:
            if provider == "roboflow":
                client = InferenceHTTPClient(
                    api_url=settings.CROP_VISION_API_URL,
                    api_key=settings.CROP_VISION_API_KEY,
                )
                image.seek(0)
                with Image.open(image) as uploaded_image:
                    model_image = uploaded_image.convert("RGB")
                label, confidence = _roboflow_prediction(
                    client.infer(model_image, model_id=settings.CROP_VISION_MODEL)
                )
                result = {
                    "possible_disease": label,
                    "confidence_pct": confidence,
                    "visual_signs": [],
                    "treatment": (
                        "This image classifier cannot confirm a disease or choose a treatment. "
                        "Ask a local extension worker to confirm the cause before treating the crop."
                    ),
                    "prevention": (
                        "Monitor nearby plants, use clean tools, and follow locally appropriate "
                        "prevention advice from an extension worker."
                    ),
                    "analysis_type": "classifier",
                }
            else:
                image_content = base64.b64encode(image.read()).decode("ascii")
                mime_type = image.image.get_format_mimetype()
                payload = {
                    "model": settings.CROP_VISION_MODEL,
                    "temperature": 0.1,
                    "max_tokens": 700,
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "Assess the crop image cautiously. You are not a definitive diagnostic tool. "
                                "Return only a JSON object with string fields possible_disease, treatment, prevention; "
                                "a number confidence_pct from 0 to 100; and a string-array visual_signs. "
                                "Name a disease only when visible evidence supports it; otherwise say uncertain and "
                                "give a low confidence. Do not invent visual signs, prescribe pesticide products, "
                                "mixtures, or application rates. Recommend local extension assessment when uncertain. "
                                "Keep treatment and prevention advice general and low risk."
                            ),
                        },
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": f"Crop: {crop.strip()}. Assess visible signs and return the requested JSON."},
                                {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{image_content}"}},
                            ],
                        },
                    ],
                }
                response = requests.post(
                    f"{settings.LLM_API_BASE_URL.rstrip('/')}/chat/completions",
                    json=payload,
                    headers={"Authorization": f"Bearer {settings.CROP_VISION_API_KEY}"},
                    timeout=settings.CROP_VISION_TIMEOUT,
                )
                response.raise_for_status()
                result = json.loads(response.json()["choices"][0]["message"]["content"])
                confidence = _confidence_pct(result["confidence_pct"])
                signs = result["visual_signs"]
                if (
                    not isinstance(result.get("possible_disease"), str)
                    or not result["possible_disease"].strip()
                    or not isinstance(signs, list)
                    or not all(isinstance(sign, str) for sign in signs)
                    or not isinstance(result.get("treatment"), str)
                    or not isinstance(result.get("prevention"), str)
                ):
                    raise ValueError("Invalid diagnosis response shape.")
                result["confidence_pct"] = confidence
                result["analysis_type"] = "vision_language"
        except (InferenceHTTPClientError, requests.RequestException, KeyError, IndexError, TypeError, ValueError):
            return Response(
                {"detail": "The vision provider is unavailable or returned an invalid diagnosis. Please try again later."},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        signs = result["visual_signs"]
        return Response({
            "crop": crop.strip(),
            "possible_disease": result["possible_disease"].strip(),
            "confidence_pct": round(float(confidence), 1),
            "visual_signs": [sign.strip() for sign in signs[:8] if sign.strip()],
            "analysis_type": result["analysis_type"],
            "treatment": result["treatment"].strip(),
            "prevention": result["prevention"].strip(),
            "disclaimer": (
                "AI image assessment only, not a confirmed diagnosis. Model-reported confidence is not calibrated "
                "or locally validated. Confirm with an extension worker before treatment."
            ),
        })


class FarmViewSet(viewsets.ModelViewSet):
    serializer_class = FarmSerializer
    permission_classes = [permissions.IsAuthenticated, CanAccessFarm]

    def get_queryset(self):
        queryset = Farm.objects.select_related("owner")
        if can_review_all(self.request.user):
            return queryset
        return queryset.filter(owner=self.request.user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    def perform_update(self, serializer):
        if serializer.instance.owner_id != self.request.user.id and self.request.user.role != User.Role.ADMIN:
            raise PermissionDenied("Only the farm owner or an administrator can edit this farm.")
        serializer.save()

    def perform_destroy(self, instance):
        if instance.owner_id != self.request.user.id and self.request.user.role != User.Role.ADMIN:
            raise PermissionDenied("Only the farm owner or an administrator can delete this farm.")
        instance.delete()


class CropViewSet(viewsets.ModelViewSet):
    serializer_class = CropSerializer
    permission_classes = [permissions.IsAuthenticated, CanManageCrop]

    def get_queryset(self):
        queryset = Crop.objects.all()
        if self.request.user.role != User.Role.ADMIN and not self.request.user.is_staff:
            return queryset.filter(active=True, verified=True)
        return queryset


class FarmQuestionViewSet(viewsets.ModelViewSet):
    serializer_class = FarmQuestionSerializer
    permission_classes = [permissions.IsAuthenticated, CanAccessQuestion]
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        queryset = FarmQuestion.objects.select_related("farm", "asked_by", "answered_by")
        if can_review_all(self.request.user):
            return queryset
        return queryset.filter(asked_by=self.request.user)

    def perform_create(self, serializer):
        farm = serializer.validated_data["farm"]
        if self.request.user.role != User.Role.FARMER or farm.owner_id != self.request.user.id:
            raise PermissionDenied("Farm questions can only be submitted by the farm owner.")
        serializer.save(asked_by=self.request.user)

    @action(detail=True, methods=["post"])
    def respond(self, request, pk=None):
        question = self.get_object()
        if not can_review_all(request.user):
            raise PermissionDenied("Extension worker access is required to respond.")
        answer = request.data.get("answer")
        if not isinstance(answer, str) or not answer.strip() or len(answer) > 4000:
            raise ValidationError({"answer": "Enter a response up to 4,000 characters."})
        question.answer = answer.strip()
        question.status = FarmQuestion.Status.RESPONDED
        question.answered_by = request.user
        question.answered_at = timezone.now()
        question.save(update_fields=["answer", "status", "answered_by", "answered_at"])
        Notification.objects.create(
            user=question.asked_by,
            farm=question.farm,
            title="Extension worker replied",
            message=f"A reply to your question about {question.farm.name} is available.",
            level="info",
        )
        return Response(FarmQuestionSerializer(question).data)


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def health(request):
    return Response({"status": "ok", "service": "AgriCloud AI API"})


@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def password_reset_request(request):
    """Send a password-reset link to the user's registered email address."""
    email = (request.data.get("email") or "").strip().lower()
    if not email:
        return Response({"email": "Enter your registered email address."}, status=status.HTTP_400_BAD_REQUEST)

    # Always return 200 so attackers cannot enumerate registered emails.
    try:
        user = User.objects.get(email__iexact=email, is_active=True)
    except User.DoesNotExist:
        return Response({"detail": "If that email is registered, a reset link has been sent."})

    from django.contrib.auth.tokens import default_token_generator
    from django.utils.encoding import force_bytes
    from django.utils.http import urlsafe_base64_encode
    from django.core.mail import send_mail
    from django.conf import settings as django_settings

    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    reset_url = f"{django_settings.FRONTEND_URL}/reset-password?uid={uid}&token={token}"

    subject = "Reset your AgriCloud AI password"
    message = (
        f"Hi {user.first_name or user.username},\n\n"
        f"We received a request to reset your AgriCloud AI password.\n\n"
        f"Click the link below to set a new password (valid for 24 hours):\n\n"
        f"{reset_url}\n\n"
        f"If you did not request this, you can ignore this email — your password will not change.\n\n"
        f"AgriCloud AI Team"
    )
    try:
        send_mail(subject, message, django_settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=False)
    except Exception:
        # Log but do not expose email errors to the client.
        import logging
        logging.getLogger(__name__).exception("Password reset email failed for user %s", user.pk)
        return Response({"detail": "Could not send the reset email. Please try again later or contact support."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    return Response({"detail": "If that email is registered, a reset link has been sent."})


@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def password_reset_confirm(request):
    """Validate the reset token and set a new password."""
    from django.contrib.auth.tokens import default_token_generator
    from django.utils.encoding import force_str
    from django.utils.http import urlsafe_base64_decode
    from django.contrib.auth.password_validation import validate_password as dj_validate
    from django.core.exceptions import ValidationError as DjangoValidationError

    uid_b64 = (request.data.get("uid") or "").strip()
    token = (request.data.get("token") or "").strip()
    new_password = request.data.get("password") or ""

    if not uid_b64 or not token:
        return Response({"detail": "Invalid reset link."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        uid = force_str(urlsafe_base64_decode(uid_b64))
        user = User.objects.get(pk=uid)
    except (User.DoesNotExist, ValueError, TypeError, OverflowError):
        return Response({"detail": "Invalid or expired reset link."}, status=status.HTTP_400_BAD_REQUEST)

    if not default_token_generator.check_token(user, token):
        return Response({"detail": "This reset link has expired or already been used. Please request a new one."}, status=status.HTTP_400_BAD_REQUEST)

    if not isinstance(new_password, str) or len(new_password) < 10:
        return Response({"password": "Your new password must be at least 10 characters."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        dj_validate(new_password, user=user)
    except DjangoValidationError as exc:
        return Response({"password": " ".join(exc.messages)}, status=status.HTTP_400_BAD_REQUEST)

    user.set_password(new_password)
    user.save(update_fields=["password"])
    return Response({"detail": "Your password has been updated. You can now sign in."})


@api_view(["POST"])
def logout(request):
    raw_token = request.data.get("refresh")
    if not raw_token:
        return Response({"refresh": "A refresh token is required."}, status=status.HTTP_400_BAD_REQUEST)
    try:
        RefreshToken(raw_token).blacklist()
    except TokenError:
        return Response({"refresh": "The refresh token is invalid or expired."}, status=status.HTTP_400_BAD_REQUEST)
    return Response({"detail": "Refresh token revoked."})


@api_view(["GET"])
def weather(request):
    farm_id = request.query_params.get("farm_id")
    if farm_id:
        try:
            farm = Farm.objects.get(pk=farm_id)
        except (Farm.DoesNotExist, ValueError):
            return Response({"detail": "Farm not found."}, status=status.HTTP_404_NOT_FOUND)
        if farm.owner_id != request.user.id and not can_review_all(request.user):
            raise PermissionDenied("You do not have access to this farm's weather.")
        latitude, longitude = farm.latitude, farm.longitude
    else:
        return Response({"detail": "farm_id is required."}, status=status.HTTP_400_BAD_REQUEST)
    start, end = request.query_params.get("start"), request.query_params.get("end")
    for label, value in (("start", start), ("end", end)):
        if value:
            try:
                date.fromisoformat(value)
            except ValueError:
                raise ValidationError({label: "Use YYYY-MM-DD format."})
    try:
        result = fetch_daily_weather(latitude, longitude, start=start, end=end)
    except ValueError as exc:
        raise ValidationError({"date_range": str(exc)}) from exc
    except WeatherServiceError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)
    result["farm"] = {"id": farm.id, "name": farm.name, "district": farm.district}
    return Response(result)


@api_view(["GET"])
def current_weather(request):
    farm_id = request.query_params.get("farm_id")
    if not farm_id:
        return Response({"detail": "farm_id is required."}, status=status.HTTP_400_BAD_REQUEST)
    try:
        farm = Farm.objects.get(pk=farm_id)
    except (Farm.DoesNotExist, ValueError, TypeError):
        return Response({"detail": "Farm not found."}, status=status.HTTP_404_NOT_FOUND)
    if farm.owner_id != request.user.id and not can_review_all(request.user):
        raise PermissionDenied("You do not have access to this farm's weather.")
    try:
        result = fetch_current_weather(farm.latitude, farm.longitude)
    except WeatherServiceError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)
    result["farm"] = {"id": farm.id, "name": farm.name, "district": farm.district}
    return Response(result)


@api_view(["POST"])
def irrigation(request):
    if not settings.IRRIGATION_ENABLED:
        return Response({"detail": "Irrigation planning is disabled by the service operator."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    farm_id = request.data.get("farm_id")
    try:
        farm = Farm.objects.get(pk=farm_id)
    except (Farm.DoesNotExist, ValueError, TypeError):
        return Response({"farm_id": "A valid farm_id is required."}, status=status.HTTP_400_BAD_REQUEST)
    if farm.owner_id != request.user.id and not can_review_all(request.user):
        raise PermissionDenied("You do not have access to this farm.")
    crop = request.data.get("crop", farm.crop)
    if not isinstance(crop, str) or not crop.strip() or len(crop.strip()) > 100:
        return Response({"crop": "Provide a crop name up to 100 characters."}, status=status.HTTP_400_BAD_REQUEST)
    stage = request.data.get("stage", "mid")
    if not isinstance(stage, str) or stage not in STAGE_COEFFICIENTS:
        return Response({"stage": f"Choose one of: {', '.join(STAGE_COEFFICIENTS)}."}, status=status.HTTP_400_BAD_REQUEST)
    soil_moisture_pct = request.data.get("soil_moisture_pct")
    if soil_moisture_pct not in (None, ""):
        if isinstance(soil_moisture_pct, bool):
            return Response({"soil_moisture_pct": "Enter a percentage from 0 to 100."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            soil_moisture_pct = float(soil_moisture_pct)
        except (TypeError, ValueError):
            return Response({"soil_moisture_pct": "Enter a percentage from 0 to 100."}, status=status.HTTP_400_BAD_REQUEST)
        if not math.isfinite(soil_moisture_pct) or not 0 <= soil_moisture_pct <= 100:
            return Response({"soil_moisture_pct": "Enter a percentage from 0 to 100."}, status=status.HTTP_400_BAD_REQUEST)
    else:
        soil_moisture_pct = None
    try:
        weather_data = fetch_current_weather(farm.latitude, farm.longitude)
        result = build_irrigation_plan(weather_data, farm, crop.strip(), stage, soil_moisture_pct)
    except WeatherServiceError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)
    except ValueError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)
    result["farm"] = {"id": farm.id, "name": farm.name, "district": farm.district}
    return Response(result)


@api_view(["POST"])
def recommendations(request):
    farm_id = request.data.get("farm_id")
    try:
        farm = Farm.objects.get(pk=farm_id)
    except (Farm.DoesNotExist, ValueError, TypeError):
        return Response({"farm_id": "A valid farm_id is required."}, status=status.HTTP_400_BAD_REQUEST)
    if farm.owner_id != request.user.id and not can_review_all(request.user):
        raise PermissionDenied("You do not have access to this farm.")
    crop = str(request.data.get("crop") or farm.crop).strip()
    if not crop or len(crop) > 100:
        return Response({"crop": "Provide a crop name up to 100 characters."}, status=status.HTTP_400_BAD_REQUEST)
    planting_date = request.data.get("planting_date")
    if planting_date:
        try:
            planting_date = date.fromisoformat(planting_date)
        except (TypeError, ValueError):
            return Response({"planting_date": "Use YYYY-MM-DD format."}, status=status.HTTP_400_BAD_REQUEST)
    try:
        weather_data = fetch_daily_weather(farm.latitude, farm.longitude).get("observations", [])
    except WeatherServiceError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)
    advice = build_planting_advice(crop, farm.soil_type, weather_data)
    record = Recommendation.objects.create(
        farm=farm,
        crop=advice["crop"],
        planting_date=planting_date or date.today(),
        guidance=advice["guidance"],
        basis=advice["basis"],
        risks=advice["risks"],
    )
    Notification.objects.create(
        user=farm.owner,
        farm=farm,
        title="Planting guidance updated",
        message=f"New {record.crop} guidance is available for {farm.name}.",
        level="info",
    )
    return Response(RecommendationSerializer(record).data, status=status.HTTP_201_CREATED)


@api_view(["GET"])
def recommendation_list(request):
    queryset = Recommendation.objects.select_related("farm")
    if not can_review_all(request.user):
        queryset = queryset.filter(farm__owner=request.user)
    farm_id = request.query_params.get("farm_id")
    if farm_id:
        queryset = queryset.filter(farm_id=farm_id)
    return Response(RecommendationSerializer(queryset[:50], many=True).data)


@api_view(["GET", "POST"])
def harvest_records(request):
    if request.method == "POST":
        serializer = HarvestRecordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        farm = serializer.validated_data["farm"]
        if farm.owner_id != request.user.id and request.user.role != User.Role.ADMIN:
            raise PermissionDenied("Only the farm owner or an administrator can record a harvest.")
        record = serializer.save(recorded_by=request.user)
        return Response(HarvestRecordSerializer(record).data, status=status.HTTP_201_CREATED)

    queryset = HarvestRecord.objects.select_related("farm", "recorded_by")
    if not can_review_all(request.user):
        queryset = queryset.filter(farm__owner=request.user)
    farm_id = request.query_params.get("farm_id")
    if farm_id:
        try:
            farm_id = int(farm_id)
        except ValueError:
            return Response({"farm_id": "Use a valid farm ID."}, status=status.HTTP_400_BAD_REQUEST)
        if farm_id <= 0:
            return Response({"farm_id": "Use a valid farm ID."}, status=status.HTTP_400_BAD_REQUEST)
        queryset = queryset.filter(farm_id=farm_id)
    crop = request.query_params.get("crop")
    if crop:
        if len(crop) > 100:
            return Response({"crop": "Crop filter must be 100 characters or fewer."}, status=status.HTTP_400_BAD_REQUEST)
        queryset = queryset.filter(crop__iexact=crop)
    return Response(HarvestRecordSerializer(queryset[:500], many=True).data)


@api_view(["GET"])
def yield_forecast(request):
    if not settings.YIELD_PREDICTION_ENABLED:
        return Response({"detail": "Yield forecasting is disabled by the service operator."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    farm_id = request.query_params.get("farm_id")
    try:
        farm = Farm.objects.get(pk=farm_id)
    except (Farm.DoesNotExist, TypeError, ValueError):
        return Response({"farm_id": "A valid farm_id is required."}, status=status.HTTP_400_BAD_REQUEST)
    if farm.owner_id != request.user.id and not can_review_all(request.user):
        raise PermissionDenied("You do not have access to this farm's yield information.")
    crop = request.query_params.get("crop") or farm.crop
    if not isinstance(crop, str) or not crop.strip() or len(crop.strip()) > 100:
        return Response({"crop": "Provide a crop name up to 100 characters."}, status=status.HTTP_400_BAD_REQUEST)
    crop = crop.strip()

    benchmarks = list(
        CropYieldBenchmark.objects.filter(
            crop__iexact=crop,
            reference_year__lte=timezone.localdate().year,
        )
        .filter(Q(district__iexact=farm.district) | Q(district=""))
        .order_by("-reference_year")[:100]
    )
    local_benchmarks = [item for item in benchmarks if item.district.casefold() == farm.district.casefold()]
    national_benchmarks = [item for item in benchmarks if not item.district]
    benchmark = (local_benchmarks or national_benchmarks or [None])[0]
    benchmark_by_year = {}
    for item in sorted(benchmarks, key=lambda row: (row.reference_year, bool(row.district)), reverse=True):
        benchmark_by_year.setdefault(item.reference_year, item)

    harvests = HarvestRecord.objects.filter(farm=farm, crop__iexact=crop)
    annual_harvests = list(
        harvests.values("harvest_date__year")
        .annotate(quantity_kg=Sum("quantity_kg"), record_count=Count("id"))
        .order_by("harvest_date__year")
    )
    personal_yield_per_hectare = None
    if annual_harvests:
        annual_quantities = [float(item["quantity_kg"]) for item in annual_harvests]
        personal_yield_per_hectare = sum(annual_quantities) / len(annual_quantities) / float(farm.size_hectares)
    forecast_yield_per_hectare = personal_yield_per_hectare
    forecast_basis = "farm_history" if personal_yield_per_hectare is not None else "benchmark" if benchmark else None
    if forecast_yield_per_hectare is None and benchmark:
        forecast_yield_per_hectare = float(benchmark.yield_kg_per_hectare)

    record_rows = list(harvests.order_by("-harvest_date", "-created_at")[:500])
    climate_context = {"available": False}
    try:
        climate_data = fetch_daily_weather(farm.latitude, farm.longitude)
        period_start = date.fromisoformat(climate_data["period"]["start"])
        period_end = date.fromisoformat(climate_data["period"]["end"])
        expected_days = (period_end - period_start).days + 1
        climate_context = {
            "available": True,
            "source": climate_data["source"],
            "period": climate_data["period"],
            **identify_climate_risks(climate_data["observations"], expected_days=expected_days),
            "methodology": (
                "Recent historical climate screening provides context only; it is not a seasonal forecast "
                "and does not adjust the benchmark-based yield estimate."
            ),
        }
    except WeatherServiceError as exc:
        climate_context["detail"] = str(exc)

    return Response({
        "farm": {"id": farm.id, "name": farm.name, "district": farm.district, "area_hectares": float(farm.size_hectares)},
        "crop": crop,
        "forecast_available": forecast_yield_per_hectare is not None,
        "reference_yield_kg_per_hectare": round(forecast_yield_per_hectare, 2) if forecast_yield_per_hectare is not None else None,
        "expected_harvest_kg": round(forecast_yield_per_hectare * float(farm.size_hectares), 2) if forecast_yield_per_hectare is not None else None,
        "forecast_basis": forecast_basis,
        "benchmark": CropYieldBenchmarkSerializer(benchmark).data if benchmark else None,
        "benchmark_trend": CropYieldBenchmarkSerializer(sorted(benchmark_by_year.values(), key=lambda row: row.reference_year), many=True).data,
        "harvest_trend": [
            {"year": item["harvest_date__year"], "quantity_kg": round(float(item["quantity_kg"]), 2), "harvest_count": item["record_count"]}
            for item in annual_harvests
        ],
        "harvest_records": HarvestRecordSerializer(record_rows, many=True).data,
        "climate_context": climate_context,
        "methodology": (
            "Expected harvest is a reference estimate: the average annual recorded farm harvest when available, "
            "otherwise the latest sourced district or national yield benchmark multiplied by farm area. "
            "Recent climate screening is shown separately and is not used as an unvalidated yield adjustment."
        ),
    })


@api_view(["GET"])
def market_intelligence(request):
    if not settings.MARKET_INTELLIGENCE_ENABLED:
        return Response({"detail": "Market intelligence is disabled by the service operator."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    commodity = request.query_params.get("commodity", "").strip()
    district = request.query_params.get("district", "").strip()
    if len(commodity) > 100 or len(district) > 100:
        return Response({"detail": "Commodity and district filters must be 100 characters or fewer."}, status=status.HTTP_400_BAD_REQUEST)
    today = timezone.localdate()
    cutoff = today - timedelta(days=365)
    queryset = MarketPrice.objects.filter(observed_at__gte=cutoff, observed_at__lte=today)
    if commodity:
        queryset = queryset.filter(commodity__iexact=commodity)
    if district:
        queryset = queryset.filter(district__iexact=district)
    prices = [
        {**dict(item), "price_type": "Administrator-entered"}
        for item in MarketPriceSerializer(queryset[:1000], many=True).data
    ]
    wfp_available = True
    try:
        wfp_prices = fetch_wfp_prices()
    except MarketDataError:
        wfp_prices = []
        wfp_available = False
    prices.extend(
        item for item in wfp_prices
        if cutoff.isoformat() <= item["observed_at"] <= today.isoformat()
        and (not commodity or item["commodity"].casefold() == commodity.casefold())
        and (not district or item["district"].casefold() == district.casefold())
    )
    prices.sort(key=lambda item: (item["observed_at"], item["commodity"], item["market"]), reverse=True)
    latest_wfp_observation = max(
        (item["observed_at"] for item in prices if item["source_title"] == SOURCE_TITLE),
        default=None,
    )
    data_note = (
        "Prices include published WFP Uganda market observations and administrator-entered records. "
        "Observation dates may be older than today's market quote; compare only matching commodities, "
        "units, currencies, and price types. Spreads exclude transport, quality and fees."
    )
    if not wfp_available:
        data_note += " The WFP feed is unavailable; only administrator-entered records are shown."
    return Response({
        "prices": prices[:5000],
        "window_start": cutoff.isoformat(),
        "data_note": data_note,
        "wfp_feed_available": wfp_available,
        "latest_wfp_observation": latest_wfp_observation,
    })


@api_view(["GET"])
def notifications(request):
    return Response(NotificationSerializer(request.user.notifications.all()[:50], many=True).data)


@api_view(["POST"])
def mark_notification_read(request, notification_id):
    try:
        notification = request.user.notifications.get(pk=notification_id)
    except Notification.DoesNotExist:
        return Response({"detail": "Notification not found."}, status=status.HTTP_404_NOT_FOUND)
    notification.read_at = timezone.now()
    notification.save(update_fields=["read_at"])
    return Response(NotificationSerializer(notification).data)


@api_view(["GET"])
def analytics(request):
    farms = Farm.objects.all() if can_review_all(request.user) else Farm.objects.filter(owner=request.user)
    summary = farms.aggregate(farm_count=Count("id"), total_hectares=Sum("size_hectares"))
    crops = list(farms.exclude(crop="").values("crop").annotate(count=Count("id")).order_by("-count")[:10])
    return Response({
        "farm_count": summary["farm_count"] or 0,
        "total_hectares": float(summary["total_hectares"] or 0),
        "crop_distribution": crops,
        "generated_at": timezone.now(),
    })


@api_view(["GET"])
def extension_overview(request):
    if not can_review_all(request.user):
        raise PermissionDenied("Extension worker access is required.")
    return Response({
        "farmers": User.objects.filter(role=User.Role.FARMER).count(),
        "farms": Farm.objects.count(),
        "districts": list(Farm.objects.values_list("district", flat=True).distinct().order_by("district")),
    })


@api_view(["GET"])
def climate_risks(request):
    farm_id = request.query_params.get("farm_id")
    try:
        farm = Farm.objects.get(pk=farm_id)
    except (Farm.DoesNotExist, ValueError, TypeError):
        return Response({"detail": "A valid farm_id is required."}, status=status.HTTP_404_NOT_FOUND)
    if farm.owner_id != request.user.id and not can_review_all(request.user):
        raise PermissionDenied("You do not have access to this farm's climate risks.")
    try:
        climate = fetch_daily_weather(farm.latitude, farm.longitude)
    except WeatherServiceError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)
    observations = climate["observations"]
    expected_days = (date.fromisoformat(climate["period"]["end"]) - date.fromisoformat(climate["period"]["start"])).days + 1
    screening = identify_climate_risks(observations, expected_days=expected_days)
    return Response({
        "farm": {"id": farm.id, "name": farm.name, "district": farm.district},
        "period": climate["period"],
        "source": climate["source"],
        **screening,
        "methodology": "Preliminary screening thresholds applied to available NASA POWER historical daily observations. Thresholds require local validation and are not forecasts or crop-loss diagnoses.",
    })


@api_view(["POST"])
def assistant_chat(request):
    question = request.data.get("message", "")
    if not isinstance(question, str) or not question.strip() or len(question) > 2000:
        return Response({"message": "Enter a question up to 2,000 characters."}, status=status.HTTP_400_BAD_REQUEST)
    if (
        not settings.LLM_API_KEY
        or not settings.LLM_MODEL
        or not settings.LLM_API_BASE_URL.lower().startswith("https://")
    ):
        return Response(
            {"detail": "The assistant requires an HTTPS LLM provider configured by an administrator."},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    messages = request.data.get("history", [])
    if not isinstance(messages, list) or len(messages) > 8:
        return Response({"history": "Provide at most 8 previous messages."}, status=status.HTTP_400_BAD_REQUEST)
    safe_messages = []
    for item in messages:
        if not isinstance(item, dict) or item.get("role") not in {"user", "assistant"} or not isinstance(item.get("content"), str):
            return Response({"history": "Each message needs a user/assistant role and text content."}, status=status.HTTP_400_BAD_REQUEST)
        safe_messages.append({"role": item["role"], "content": item["content"][:2000]})
    previous_question = next(
        (item["content"] for item in reversed(safe_messages) if item["role"] == "user"),
        "",
    )
    retrieval_query = f"{previous_question}\n{question.strip()}" if previous_question else question.strip()
    knowledge, sources = retrieve_knowledge(retrieval_query, settings.AGRICULTURE_KNOWLEDGE_CONTEXT)
    context_instructions = (
        f"Verified knowledge context retrieved for this question:\n{knowledge[:20000]}"
        if knowledge
        else "No relevant verified agricultural source matched this question or its recent user-question context. "
        "Do not present any answer as locally verified."
    )
    payload = {
        "model": settings.LLM_MODEL,
        "temperature": 0.2,
        "max_tokens": 512,
        "messages": [
            {"role": "system", "content": (
                "You are a friendly, conversational agricultural information assistant for farmers in Uganda. "
                "Respond naturally to greetings and follow-up questions, keep answers concise, and use simple English. "
                "When verified source context is provided, base crop-specific claims on it and cite its source titles where available. "
                "When no relevant verified context is provided, answer general, low-risk questions when you can, clearly disclose that the guidance is general and not locally verified, "
                "and ask a focused follow-up question when details matter. If you cannot answer reliably, say what is missing and recommend contacting a district extension worker. "
                "Never invent sources, diagnoses, forecasts, pesticide or fertilizer rates, mixtures, or scientific certainty. "
                "Only repeat specific treatment rates if a supplied verified source explicitly supports them, and remind users to follow product labels and local extension advice. "
                "Distinguish historical observations from forecasts. Do not request or infer private farm or account details.\n\n"
                f"{context_instructions}"
            )},
            *safe_messages,
            {"role": "user", "content": question.strip()},
        ],
    }
    try:
        response = requests.post(
            f"{settings.LLM_API_BASE_URL.rstrip('/')}/chat/completions",
            json=payload,
            headers={"Authorization": f"Bearer {settings.LLM_API_KEY}"},
            timeout=30,
        )
        response.raise_for_status()
        answer = response.json()["choices"][0]["message"]["content"]
    except (requests.RequestException, KeyError, IndexError, TypeError, ValueError) as exc:
        return Response({"detail": "The assistant provider is temporarily unavailable."}, status=status.HTTP_502_BAD_GATEWAY)
    return Response({"answer": answer, "sources": sources, "grounded": bool(knowledge)})
