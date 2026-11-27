from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AdminOverviewView, AdminUsersView, CropViewSet, FarmQuestionViewSet, FarmViewSet, MeView, ProfileImageView, RegisterView, analytics, extension_overview, health,
    assistant_chat, climate_risks, current_weather, CropDiseaseView, harvest_records, irrigation, logout, market_intelligence, mark_notification_read, notifications, password_reset_confirm, password_reset_request, recommendation_list, recommendations, weather, yield_forecast,
)

router = DefaultRouter()
router.register("farms", FarmViewSet, basename="farm")
router.register("crops", CropViewSet, basename="crop")
router.register("questions", FarmQuestionViewSet, basename="question")

urlpatterns = [
    path("health/", health),
    path("auth/register/", RegisterView.as_view(), name="register"),
    path("admin/overview/", AdminOverviewView.as_view(), name="admin-overview"),
    path("admin/users/", AdminUsersView.as_view(), name="admin-users"),
    path("admin/users/<int:user_id>/", AdminUsersView.as_view(), name="admin-user-detail"),
    path("auth/me/", MeView.as_view(), name="me"),
    path("auth/me/profile-image/", ProfileImageView.as_view(), name="profile-image"),
    path("auth/logout/", logout, name="logout"),
    path("auth/password-reset/", password_reset_request, name="password-reset-request"),
    path("auth/password-reset/confirm/", password_reset_confirm, name="password-reset-confirm"),
    path("weather/", weather, name="weather"),
    path("weather/current/", current_weather, name="current-weather"),
    path("crop-disease/", CropDiseaseView.as_view(), name="crop-disease"),
    path("irrigation/", irrigation, name="irrigation"),
    path("yield-forecast/", yield_forecast, name="yield-forecast"),
    path("harvests/", harvest_records, name="harvest-records"),
    path("market-intelligence/", market_intelligence, name="market-intelligence"),
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
