from datetime import date
import requests

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import Count, Sum
from django.utils import timezone
from rest_framework import generics, permissions, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Crop, Farm, FarmQuestion, Notification, Recommendation
from .permissions import CanAccessFarm, CanAccessQuestion, CanManageCrop
from .serializers import CropSerializer, FarmQuestionSerializer, FarmSerializer, NotificationSerializer, RecommendationSerializer, RegisterSerializer, UserSerializer
from .services.nasa_power import WeatherServiceError, fetch_daily_weather
from .services.agriculture_knowledge import retrieve_knowledge
from .services.recommendations import build_planting_advice
from .services.risks import identify_climate_risks

User = get_user_model()


def can_review_all(user):
    return user.role in {User.Role.EXTENSION, User.Role.ADMIN} or user.is_staff


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

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
