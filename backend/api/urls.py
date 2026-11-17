from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    CropViewSet, FarmQuestionViewSet, FarmViewSet, MeView, RegisterView, analytics, extension_overview, health,
    assistant_chat, climate_risks, logout, mark_notification_read, notifications, recommendation_list, recommendations, weather,
)

router = DefaultRouter()
router.register("farms", FarmViewSet, basename="farm")
router.register("crops", CropViewSet, basename="crop")
router.register("questions", FarmQuestionViewSet, basename="question")

urlpatterns = [
    path("health/", health),
    path("auth/register/", RegisterView.as_view(), name="register"),
    path("auth/me/", MeView.as_view(), name="me"),
    path("auth/logout/", logout, name="logout"),
    path("weather/", weather, name="weather"),
    path("recommendations/", recommendations, name="recommendations"),
    path("recommendations/list/", recommendation_list, name="recommendation-list"),
    path("notifications/", notifications, name="notifications"),
    path("notifications/<int:notification_id>/read/", mark_notification_read, name="notification-read"),
    path("analytics/", analytics, name="analytics"),
    path("extension/overview/", extension_overview, name="extension-overview"),
    path("assistant/chat/", assistant_chat, name="assistant-chat"),
    path("risks/", climate_risks, name="climate-risks"),
    path("", include(router.urls)),
]
