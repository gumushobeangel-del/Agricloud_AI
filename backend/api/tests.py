from datetime import date, timedelta
from io import BytesIO
import json
from pathlib import Path
import tempfile
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone
from PIL import Image
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Crop, CropYieldBenchmark, Farm, FarmQuestion, HarvestRecord, MarketPrice
from .services.nasa_power import WeatherServiceError, fetch_daily_weather
from .services.open_meteo import fetch_current_weather
from .services.agriculture_knowledge import retrieve_knowledge
from .services.risks import identify_climate_risks
from .services.irrigation import build_irrigation_plan
from .services.market_prices import MarketDataError, fetch_wfp_prices

User = get_user_model()


class FarmApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.owner = User.objects.create_user(username="farmer", password="StrongPass123!")
        self.other = User.objects.create_user(username="other", password="StrongPass123!")
        self.client.force_authenticate(self.owner)
        self.payload = {
            "name": "Kawanda plot", "district": "Wakiso", "crop": "maize",
            "size_hectares": "1.25", "latitude": "0.4190", "longitude": "32.5540",
            "soil_type": "loam",
        }

    def test_create_and_list_farm(self):
        created = self.client.post("/api/farms/", self.payload, format="json")
        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.data["owner"], self.owner.id)
        self.assertEqual(len(self.client.get("/api/farms/").data), 1)

    def test_owner_can_update_and_delete_farm(self):
        created = self.client.post("/api/farms/", self.payload, format="json")
        farm_id = created.data["id"]
        updated = self.client.patch(f"/api/farms/{farm_id}/", {"name": "North plot"}, format="json")
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.data["name"], "North plot")
        deleted = self.client.delete(f"/api/farms/{farm_id}/")
        self.assertEqual(deleted.status_code, 204)
        self.assertEqual(self.client.get("/api/farms/").data, [])

    def test_jwt_login_returns_tokens(self):
        response = self.client.post("/api/auth/token/", {"username": "farmer", "password": "StrongPass123!"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_logout_blacklists_refresh_token(self):
        token = str(RefreshToken.for_user(self.owner))
        response = self.client.post("/api/auth/logout/", {"refresh": token}, format="json")
        self.assertEqual(response.status_code, 200)
        rejected = self.client.post("/api/auth/token/refresh/", {"refresh": token}, format="json")
        self.assertEqual(rejected.status_code, 401)

    def test_coordinates_are_validated(self):
        response = self.client.post("/api/farms/", {**self.payload, "latitude": "100"}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_farm_data_is_private(self):
        farm = Farm.objects.create(owner=self.other, name="Private", district="Mbale", size_hectares=1, latitude=1, longitude=34)
        self.assertEqual(self.client.get(f"/api/farms/{farm.id}/").status_code, 404)
        self.assertEqual(self.client.delete(f"/api/farms/{farm.id}/").status_code, 404)


class RegistrationTests(TestCase):
    def test_registration_cannot_self_assign_privileged_role(self):
        response = self.client.post("/api/auth/register/", {
            "username": "newfarmer", "email": "farmer@example.test",
            "password": "StrongPass123!", "role": "admin",
        }, content_type="application/json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["user"]["role"], "farmer")
        self.assertIn("access", response.data)

    @override_settings(LLM_API_KEY="", LLM_MODEL="", AGRICULTURE_KNOWLEDGE_CONTEXT="")
    def test_assistant_requires_provider_configuration(self):
        user = User.objects.create_user(username="asker", password="StrongPass123!")
        client = APIClient()
        client.force_authenticate(user)
        response = client.post("/api/assistant/chat/", {"message": "When should I plant maize?"}, format="json")
        self.assertEqual(response.status_code, 503)


class ProfileImageApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="photoowner", password="StrongPass123!")
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def image_upload(self, name="profile.png"):
        image_data = BytesIO()
        Image.new("RGB", (4, 4), color=(28, 120, 76)).save(image_data, format="PNG")
        return SimpleUploadedFile(name, image_data.getvalue(), content_type="image/png")

    def test_user_can_upload_replace_and_remove_profile_picture(self):
        with tempfile.TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            uploaded = self.client.post(
                "/api/auth/me/profile-image/",
                {"profile_image": self.image_upload()},
                format="multipart",
            )
            self.assertEqual(uploaded.status_code, 200)
            self.assertTrue(uploaded.data["profile_image"].startswith("/media/profile-pictures/"))
            self.user.refresh_from_db()
            original_path = self.user.profile_image.path
            self.assertTrue(Path(original_path).exists())

            replaced = self.client.post(
                "/api/auth/me/profile-image/",
                {"profile_image": self.image_upload()},
                format="multipart",
            )
            self.assertEqual(replaced.status_code, 200)
            self.user.refresh_from_db()
            self.assertNotEqual(self.user.profile_image.path, original_path)
            self.assertFalse(Path(original_path).exists())

            removed = self.client.delete("/api/auth/me/profile-image/")
            self.assertEqual(removed.status_code, 200)
            self.assertIsNone(removed.data["profile_image"])

    def test_upload_rejects_non_image_content(self):
        response = self.client.post(
            "/api/auth/me/profile-image/",
            {"profile_image": SimpleUploadedFile("fake.png", b"not an image", content_type="image/png")},
            format="multipart",
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(User.objects.get(pk=self.user.pk).profile_image)

    def test_upload_rejects_images_larger_than_five_megabytes(self):
        image = self.image_upload()
        oversized_image = image.read() + b"x" * (5 * 1024 * 1024 + 1)
        response = self.client.post(
            "/api/auth/me/profile-image/",
            {"profile_image": SimpleUploadedFile("large.png", oversized_image, content_type="image/png")},
            format="multipart",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("5 MB", str(response.data))


class CropDiseaseApiTests(TestCase):
    @override_settings(CROP_VISION_ENABLED=False)
    @patch("api.views.InferenceHTTPClient")
    def test_crop_analysis_can_be_disabled_by_operator(self, client_factory):
        user = User.objects.create_user(username="disabledvision", password="StrongPass123!")
        client = APIClient()
        client.force_authenticate(user)

        response = client.post("/api/crop-disease/", {"crop": "Maize"}, format="multipart")

        self.assertEqual(response.status_code, 503)
        client_factory.assert_not_called()

    @override_settings(
        CROP_VISION_ENABLED=True,
        CROP_VISION_PROVIDER="openai-compatible",
        CROP_VISION_API_KEY="test-key",
        LLM_API_KEY="test-key",
        LLM_API_BASE_URL="https://provider.example/v1",
        CROP_VISION_MODEL="vision-model",
    )
    @patch("api.views.requests.post")
    def test_crop_image_is_analyzed_without_saving_it(self, provider_post):
        user = User.objects.create_user(username="cropvisionfarmer", password="StrongPass123!")
        client = APIClient()
        client.force_authenticate(user)
        image_data = BytesIO()
        Image.new("RGB", (4, 4), color=(28, 120, 76)).save(image_data, format="PNG")
        image = SimpleUploadedFile("leaf.png", image_data.getvalue(), content_type="image/png")
        provider_post.return_value.json.return_value = {"choices": [{"message": {"content": json.dumps({
            "possible_disease": "Possible leaf spot",
            "confidence_pct": 71,
            "visual_signs": ["Small dark lesions"],
            "treatment": "Seek local assessment before treatment.",
            "prevention": "Use clean tools and monitor nearby plants.",
        })}}]}

        response = client.post("/api/crop-disease/", {"crop": "Maize", "image": image}, format="multipart")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["confidence_pct"], 71)
        self.assertIn("not calibrated", response.data["disclaimer"])
        prompt = provider_post.call_args.kwargs["json"]["messages"][1]["content"]
        self.assertEqual(prompt[1]["type"], "image_url")

    @override_settings(
        CROP_VISION_ENABLED=True,
        CROP_VISION_PROVIDER="openai-compatible",
        CROP_VISION_API_KEY="",
        LLM_API_KEY="",
        CROP_VISION_MODEL="",
    )
    def test_crop_diagnosis_is_unavailable_without_configured_vision_provider(self):
        user = User.objects.create_user(username="unconfiguredvision", password="StrongPass123!")
        client = APIClient()
        client.force_authenticate(user)
        response = client.post("/api/crop-disease/", {"crop": "Maize"}, format="multipart")
        self.assertEqual(response.status_code, 503)

    @override_settings(
        CROP_VISION_ENABLED=True,
        CROP_VISION_PROVIDER="roboflow",
        CROP_VISION_API_KEY="test-key",
        CROP_VISION_API_URL="https://detect.roboflow.com",
        CROP_VISION_MODEL="leaf-model/1",
    )
    @patch("api.views.InferenceHTTPClient")
    def test_roboflow_classifier_response_is_normalized(self, client_factory):
        user = User.objects.create_user(username="roboflowfarmer", password="StrongPass123!")
        client = APIClient()
        client.force_authenticate(user)
        image_data = BytesIO()
        Image.new("RGB", (4, 4), color=(28, 120, 76)).save(image_data, format="PNG")
        image = SimpleUploadedFile("leaf.png", image_data.getvalue(), content_type="image/png")
        client_factory.return_value.infer.return_value = {
            "top": "leaf-blight",
            "predictions": {"healthy": 0.08, "leaf-blight": 0.92},
        }

        response = client.post("/api/crop-disease/", {"crop": "Maize", "image": image}, format="multipart")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["possible_disease"], "leaf-blight")
        self.assertEqual(response.data["confidence_pct"], 92)
        self.assertEqual(response.data["analysis_type"], "classifier")
        self.assertEqual(response.data["visual_signs"], [])
        self.assertIn("cannot confirm", response.data["treatment"])
        client_factory.return_value.infer.assert_called_once()


class AssistantApiTests(TestCase):
    @override_settings(
        LLM_API_KEY="test-key",
        LLM_API_BASE_URL="https://provider.example/v1",
        LLM_MODEL="test-model",
        AGRICULTURE_KNOWLEDGE_CONTEXT=(
            "Source: Rice field note\n"
            "Reviewed material about rice leaf yellowing and local assessment."
        ),
    )
    @patch("api.views.requests.post")
    def test_assistant_caps_completion_tokens(self, provider_post):
        provider_post.return_value.json.return_value = {
            "choices": [{"message": {"content": "Consult the referenced field note."}}],
        }
        user = User.objects.create_user(username="assistantfarmer", password="StrongPass123!")
        client = APIClient()
        client.force_authenticate(user)

        response = client.post(
            "/api/assistant/chat/",
            {"message": "Why are rice leaves yellow?", "history": []},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(provider_post.call_args.kwargs["json"]["max_tokens"], 512)
        self.assertEqual(response.data["sources"], ["Rice field note"])
        self.assertTrue(response.data["grounded"])

    @override_settings(
        LLM_API_KEY="test-key",
        LLM_API_BASE_URL="https://provider.example/v1",
        LLM_MODEL="test-model",
        AGRICULTURE_KNOWLEDGE_CONTEXT="",
    )
    @patch("api.views.requests.post")
    def test_assistant_can_chat_without_knowledge_context(self, provider_post):
        provider_post.return_value.json.return_value = {
            "choices": [{"message": {"content": "Hello! What would you like help with on your farm?"}}],
        }
        user = User.objects.create_user(username="emptycontextfarmer", password="StrongPass123!")
        client = APIClient()
        client.force_authenticate(user)

        response = client.post(
            "/api/assistant/chat/",
            {"message": "Hello", "history": []},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["sources"], [])
        self.assertFalse(response.data["grounded"])
        provider_post.assert_called_once()

    @override_settings(
        LLM_API_KEY="test-key",
        LLM_API_BASE_URL="https://provider.example/v1",
        LLM_MODEL="test-model",
        AGRICULTURE_KNOWLEDGE_CONTEXT=(
            "Source: Rice field note\n"
            "Reviewed material about rice leaf yellowing and local assessment."
        ),
    )
    @patch("api.views.requests.post")
    def test_assistant_responds_without_matching_context(self, provider_post):
        provider_post.return_value.json.return_value = {
            "choices": [{"message": {"content": "Yellow leaves can have several causes. What crop are you growing?"}}],
        }
        user = User.objects.create_user(username="generalassistantfarmer", password="StrongPass123!")
        client = APIClient()
        client.force_authenticate(user)

        response = client.post(
            "/api/assistant/chat/",
            {"message": "How do I prepare a seedbed?", "history": []},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["answer"], "Yellow leaves can have several causes. What crop are you growing?")
        self.assertEqual(response.data["sources"], [])
        self.assertFalse(response.data["grounded"])
        self.assertIn("Do not present any answer as locally verified", provider_post.call_args.kwargs["json"]["messages"][0]["content"])

    @override_settings(
        LLM_API_KEY="test-key",
        LLM_API_BASE_URL="https://provider.example/v1",
        LLM_MODEL="test-model",
        AGRICULTURE_KNOWLEDGE_CONTEXT=(
            "Source: Rice field note\n"
            "Reviewed material about rice leaf yellowing and local assessment."
        ),
    )
    @patch("api.views.requests.post")
    def test_assistant_uses_previous_user_question_for_follow_ups(self, provider_post):
        provider_post.return_value.json.return_value = {
            "choices": [{"message": {"content": "Check the crop and symptoms with a local extension worker."}}],
        }
        user = User.objects.create_user(username="followupfarmer", password="StrongPass123!")
        client = APIClient()
        client.force_authenticate(user)

        response = client.post(
            "/api/assistant/chat/",
            {
                "message": "What should I check next?",
                "history": [
                    {"role": "user", "content": "Why are rice leaves yellow?"},
                    {"role": "assistant", "content": "Yellowing can have several causes."},
                ],
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["sources"], ["Rice field note"])
        self.assertTrue(response.data["grounded"])


class CropCatalogTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.farmer = User.objects.create_user(username="cropfarmer", password="StrongPass123!")
        self.admin = User.objects.create_user(username="catalogadmin", password="StrongPass123!", role="admin")
        self.assertTrue(self.admin.is_staff)

    def test_public_catalog_only_shows_verified_active_crops(self):
        Crop.objects.create(name="Verified beans", verified=True, source_title="District guide", source_url="https://example.org/guide")
        Crop.objects.create(name="Draft crop")
        Crop.objects.create(name="Inactive crop", verified=True, active=False, source_title="Guide", source_url="https://example.org/guide")
        self.client.force_authenticate(self.farmer)
        response = self.client.get("/api/crops/")
        self.assertEqual([item["name"] for item in response.data], ["Verified beans"])

    def test_only_administrators_can_manage_verified_crop_sources(self):
        self.client.force_authenticate(self.farmer)
        denied = self.client.post("/api/crops/", {"name": "Beans", "verified": True, "source_title": "Guide", "source_url": "https://example.org"}, format="json")
        self.assertEqual(denied.status_code, 403)
        self.client.force_authenticate(self.admin)
        invalid = self.client.post("/api/crops/", {"name": "Beans", "verified": True}, format="json")
        self.assertEqual(invalid.status_code, 400)
        created = self.client.post("/api/crops/", {"name": "Beans", "verified": True, "source_title": "Guide", "source_url": "https://example.org"}, format="json")
        self.assertEqual(created.status_code, 201)


class QuestionWorkflowTests(TestCase):
    def setUp(self):
        self.farmer = User.objects.create_user(username="questionfarmer", password="StrongPass123!")
        self.extension = User.objects.create_user(username="extensionworker", password="StrongPass123!", role="extension")
        self.farm = Farm.objects.create(owner=self.farmer, name="East field", district="Mbale", size_hectares=2, latitude=1.1, longitude=34.2)

    def test_farmer_can_submit_and_extension_can_reply(self):
        farmer_client = APIClient()
        farmer_client.force_authenticate(self.farmer)
        submitted = farmer_client.post("/api/questions/", {"farm": self.farm.id, "question": "How can I check soil drainage?"}, format="json")
        self.assertEqual(submitted.status_code, 201)

        extension_client = APIClient()
        extension_client.force_authenticate(self.extension)
        self.assertEqual(len(extension_client.get("/api/questions/").data), 1)
        response = extension_client.post(f"/api/questions/{submitted.data['id']}/respond/", {"answer": "Observe water movement after rain and ask your district extension worker for locally suitable tests."}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], FarmQuestion.Status.RESPONDED)
        self.assertEqual(self.farmer.notifications.count(), 1)

    def test_farmer_cannot_view_another_users_question(self):
        question = FarmQuestion.objects.create(farm=self.farm, asked_by=self.farmer, question="Private question")
        other = User.objects.create_user(username="anotherfarmer", password="StrongPass123!")
        client = APIClient()
        client.force_authenticate(other)
        self.assertEqual(client.get(f"/api/questions/{question.id}/").status_code, 404)


class WeatherServiceTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="weatherfarmer", password="StrongPass123!")
        self.client = APIClient()

    @override_settings(NASA_POWER_BASE_URL="https://example.test/power")
    @patch("api.services.nasa_power.requests.get")
    def test_weather_handles_missing_values_and_caches(self, get):
        start = date.today() - timedelta(days=4)
        end = date.today() - timedelta(days=2)
        payload = {"properties": {"parameter": {
            "PRECTOTCORR": {start.strftime("%Y%m%d"): 2.5},
            "T2M": {start.strftime("%Y%m%d"): 22.0},
            "RH2M": {start.strftime("%Y%m%d"): -999.0},
            "ALLSKY_SFC_SW_DWN": {start.strftime("%Y%m%d"): 4.1},
        }}}
        response = Mock()
        response.json.return_value = payload
        response.raise_for_status.return_value = None
        get.return_value = response
        first = fetch_daily_weather(0.419, 32.554, start.isoformat(), end.isoformat())
        second = fetch_daily_weather(0.419, 32.554, start.isoformat(), end.isoformat())
        self.assertFalse(first["is_forecast"])
        self.assertEqual(first["observations"][0]["values"]["T2M"]["value"], 22.0)
        self.assertNotIn("RH2M", first["observations"][0]["values"])
        self.assertEqual(first, second)
        get.assert_called_once()

    def test_weather_rejects_today_as_observation_end(self):
        with self.assertRaises(ValueError):
            fetch_daily_weather(0, 32, end=date.today().isoformat())

    @override_settings(NASA_POWER_BASE_URL="https://example.test/power")
    @patch("api.services.nasa_power.requests.get", side_effect=__import__("requests").Timeout())
    def test_weather_reports_upstream_failure(self, get):
        with self.assertRaises(WeatherServiceError):
            fetch_daily_weather(0.419, 32.554)

    @patch("api.views.fetch_daily_weather")
    def test_weather_endpoint_returns_historical_data(self, fetch):
        farm = Farm.objects.create(owner=self.owner, name="Kawanda", district="Wakiso", size_hectares=1, latitude=0.419, longitude=32.554)
        self.client.force_authenticate(self.owner)
        fetch.return_value = {"source": "NASA POWER", "data_type": "historical_observations", "is_forecast": False, "observations": []}
        response = self.client.get(f"/api/weather/?farm_id={farm.id}")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["is_forecast"])
        self.assertEqual(response.data["farm"]["id"], farm.id)
        fetch.assert_called_once()

    @patch("api.views.fetch_daily_weather")
    def test_recommendation_uses_server_climate_data(self, fetch):
        farm = Farm.objects.create(owner=self.owner, name="Kawanda", district="Wakiso", crop="maize", soil_type="loam", size_hectares=1, latitude=0.419, longitude=32.554)
        self.client.force_authenticate(self.owner)
        fetch.return_value = {"observations": [{"values": {"PRECTOTCORR": {"value": 20.0}}}]}
        response = self.client.post("/api/recommendations/", {"farm_id": farm.id, "crop": "beans"}, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["crop"], "beans")
        self.assertTrue(response.data["basis"])
        self.assertEqual(self.owner.notifications.count(), 1)
        fetch.assert_called_once()

    def test_notification_read_is_scoped_to_its_owner(self):
        farm = Farm.objects.create(owner=self.owner, name="Kawanda", district="Wakiso", size_hectares=1, latitude=0.419, longitude=32.554)
        from .models import Notification
        notification = Notification.objects.create(user=self.owner, farm=farm, title="Update", message="Guidance is ready.")
        other = User.objects.create_user(username="weatherother", password="StrongPass123!")
        self.client.force_authenticate(other)
        self.assertEqual(self.client.post(f"/api/notifications/{notification.id}/read/").status_code, 404)
        self.client.force_authenticate(self.owner)
        response = self.client.post(f"/api/notifications/{notification.id}/read/")
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.data["read_at"])


class IrrigationPlanTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="irrigationowner", password="StrongPass123!")
        self.client = APIClient()

    @override_settings(IRRIGATION_ENABLED=False)
    @patch("api.views.fetch_current_weather")
    def test_irrigation_can_be_disabled_by_operator(self, fetch):
        self.client.force_authenticate(self.owner)
        response = self.client.post("/api/irrigation/", {"farm_id": 1}, format="json")
        self.assertEqual(response.status_code, 503)
        fetch.assert_not_called()

    def test_irrigation_plan_uses_forecast_and_reports_field_volume(self):
        farm = Farm.objects.create(
            owner=self.owner, name="Kawanda", district="Wakiso", crop="maize",
            soil_type="loam", size_hectares=2, latitude=0.419, longitude=32.554,
        )
        weather = {
            "source": "Open-Meteo",
            "daily_forecast": [
                {"date": "2026-11-18", "et0_mm": 5, "precipitation_sum_mm": 0},
                {"date": "2026-11-19", "et0_mm": 4, "precipitation_sum_mm": 1},
            ],
        }

        plan = build_irrigation_plan(weather, farm, "maize", "mid", 25)

        self.assertEqual(plan["daily"][0]["crop_water_need_mm"], 6.0)
        self.assertEqual(plan["daily"][1]["effective_rainfall_mm"], 0.8)
        self.assertEqual(plan["totals"]["net_irrigation_volume_liters"], 200000)
        self.assertEqual(plan["soil_moisture_pct"], 25)
        self.assertTrue(plan["soil_moisture_note"])
        self.assertTrue(plan["schedule"])

    def test_irrigation_plan_requires_complete_weather_water_inputs(self):
        farm = Farm.objects.create(
            owner=self.owner, name="Kawanda", district="Wakiso", crop="maize",
            soil_type="loam", size_hectares=1, latitude=0.419, longitude=32.554,
        )
        with self.assertRaisesRegex(ValueError, "evapotranspiration and rainfall"):
            build_irrigation_plan(
                {"daily_forecast": [{"date": "2026-11-18", "precipitation_sum_mm": 1}]},
                farm,
                "maize",
                "mid",
            )

    @patch("api.views.fetch_current_weather")
    def test_irrigation_endpoint_returns_forecast_plan(self, fetch):
        farm = Farm.objects.create(
            owner=self.owner, name="Kawanda", district="Wakiso", crop="maize",
            soil_type="loam", size_hectares=1, latitude=0.419, longitude=32.554,
        )
        self.client.force_authenticate(self.owner)
        fetch.return_value = {
            "source": "Open-Meteo",
            "daily_forecast": [
                {"date": "2026-11-18", "et0_mm": 5, "precipitation_sum_mm": 0},
            ],
        }

        response = self.client.post("/api/irrigation/", {"farm_id": farm.id}, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["farm"]["id"], farm.id)
        self.assertEqual(response.data["crop"], "maize")
        fetch.assert_called_once()

    @patch("api.views.fetch_current_weather")
    def test_irrigation_endpoint_is_scoped_to_farm_owner(self, fetch):
        other_farm = Farm.objects.create(
            owner=User.objects.create_user(username="irrigationprivate", password="StrongPass123!"),
            name="Private", district="Mbale", size_hectares=1, latitude=1.1, longitude=34.2,
        )
        self.client.force_authenticate(self.owner)
        response = self.client.post("/api/irrigation/", {"farm_id": other_farm.id}, format="json")
        self.assertEqual(response.status_code, 403)
        fetch.assert_not_called()


class YieldAndMarketApiTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="yieldowner", password="StrongPass123!")
        self.other = User.objects.create_user(username="yieldother", password="StrongPass123!")
        self.farm = Farm.objects.create(
            owner=self.owner, name="Kawanda", district="Wakiso", crop="maize",
            size_hectares=2, latitude=0.419, longitude=32.554,
        )
        self.client = APIClient()
        self.client.force_authenticate(self.owner)

    @override_settings(YIELD_PREDICTION_ENABLED=False)
    @patch("api.views.fetch_daily_weather")
    def test_yield_forecasting_can_be_disabled_by_operator(self, fetch):
        response = self.client.get(f"/api/yield-forecast/?farm_id={self.farm.id}")
        self.assertEqual(response.status_code, 503)
        fetch.assert_not_called()

    @patch("api.views.fetch_daily_weather")
    def test_yield_forecast_uses_farm_harvest_history_and_separate_climate_context(self, fetch):
        prior_year = date.today().year - 1
        HarvestRecord.objects.create(
            farm=self.farm, crop="maize", harvest_date=date(prior_year, 6, 1),
            quantity_kg=600, recorded_by=self.owner,
        )
        HarvestRecord.objects.create(
            farm=self.farm, crop="maize", harvest_date=date.today() - timedelta(days=1),
            quantity_kg=1000, recorded_by=self.owner,
        )
        CropYieldBenchmark.objects.create(
            crop="maize", district="Wakiso", reference_year=prior_year,
            yield_kg_per_hectare=300, source_title="District survey",
            source_url="https://example.test/yield",
        )
        start = date.today() - timedelta(days=2)
        end = date.today() - timedelta(days=1)
        fetch.return_value = {
            "source": "NASA POWER",
            "period": {"start": start.isoformat(), "end": end.isoformat()},
            "observations": [{"date": start.isoformat(), "values": {"PRECTOTCORR": {"value": 0.0}}}],
        }

        response = self.client.get(f"/api/yield-forecast/?farm_id={self.farm.id}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["forecast_basis"], "farm_history")
        self.assertEqual(response.data["reference_yield_kg_per_hectare"], 400)
        self.assertEqual(response.data["expected_harvest_kg"], 800)
        self.assertEqual(len(response.data["harvest_trend"]), 2)
        self.assertEqual(response.data["benchmark"]["source_title"], "District survey")
        self.assertTrue(response.data["climate_context"]["available"])
        self.assertIn("does not adjust", response.data["climate_context"]["methodology"])

    @patch("api.views.fetch_daily_weather")
    def test_yield_forecast_does_not_invent_baseline_without_records(self, fetch):
        fetch.return_value = {
            "source": "NASA POWER",
            "period": {"start": date.today().isoformat(), "end": date.today().isoformat()},
            "observations": [],
        }
        response = self.client.get(f"/api/yield-forecast/?farm_id={self.farm.id}")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["forecast_available"])
        self.assertIsNone(response.data["expected_harvest_kg"])

    @patch("api.views.fetch_daily_weather")
    def test_yield_forecast_rejects_another_users_farm(self, fetch):
        private_farm = Farm.objects.create(
            owner=self.other, name="Private", district="Mbale", crop="maize",
            size_hectares=1, latitude=1.1, longitude=34.2,
        )
        response = self.client.get(f"/api/yield-forecast/?farm_id={private_farm.id}")
        self.assertEqual(response.status_code, 403)
        fetch.assert_not_called()

    def test_owner_can_record_harvest_and_records_remain_private(self):
        response = self.client.post("/api/harvests/", {
            "farm": self.farm.id,
            "crop": "maize",
            "harvest_date": date.today().isoformat(),
            "quantity_kg": "850.5",
        }, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["quantity_kg"], "850.50")
        self.assertEqual(self.client.get(f"/api/harvests/?farm_id={self.farm.id}").data[0]["id"], response.data["id"])
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.get(f"/api/harvests/?farm_id={self.farm.id}").data, [])
        denied = self.client.post("/api/harvests/", {
            "farm": self.farm.id,
            "crop": "maize",
            "harvest_date": date.today().isoformat(),
            "quantity_kg": "10",
        }, format="json")
        self.assertEqual(denied.status_code, 403)

    @patch("api.views.fetch_wfp_prices", return_value=[])
    def test_market_prices_filter_and_keep_source_attribution(self, fetch_prices):
        price = MarketPrice.objects.create(
            commodity="maize", market="Kalerwe", district="Kampala",
            price="1200", unit="kg", currency="UGX", observed_at=date.today() - timedelta(days=1),
            source_title="Market survey", source_url="https://example.test/prices",
        )
        MarketPrice.objects.create(
            commodity="beans", market="Kalerwe", district="Kampala",
            price="2400", unit="kg", currency="UGX", observed_at=date.today() - timedelta(days=1),
            source_title="Market survey", source_url="https://example.test/prices",
        )

        response = self.client.get("/api/market-intelligence/?commodity=maize&district=Kampala")

        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["id"] for item in response.data["prices"]], [price.id])
        self.assertEqual(response.data["prices"][0]["source_title"], "Market survey")
        self.assertEqual(response.data["prices"][0]["price_type"], "Administrator-entered")
        self.assertTrue(response.data["wfp_feed_available"])
        self.assertIn("transport", response.data["data_note"])

    @patch("api.views.fetch_wfp_prices")
    def test_market_intelligence_combines_wfp_prices_with_matching_filters(self, fetch_prices):
        observed_at = timezone.localdate().isoformat()
        fetch_prices.return_value = [{
            "id": "wfp-test",
            "commodity": "Maize",
            "market": "Kalerwe",
            "district": "Kampala",
            "price": "1500",
            "unit": "KG",
            "currency": "UGX",
            "observed_at": observed_at,
            "price_type": "Retail",
            "source_title": "WFP Uganda Food Prices (HDX)",
            "source_url": "https://data.humdata.org/dataset/wfp-food-prices-for-uganda",
        }, {
            "id": "wfp-other",
            "commodity": "Beans",
            "market": "Kalerwe",
            "district": "Kampala",
            "price": "2000",
            "unit": "KG",
            "currency": "UGX",
            "observed_at": observed_at,
            "price_type": "Retail",
            "source_title": "WFP Uganda Food Prices (HDX)",
            "source_url": "https://data.humdata.org/dataset/wfp-food-prices-for-uganda",
        }]

        response = self.client.get("/api/market-intelligence/?commodity=maize&district=Kampala")

        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["id"] for item in response.data["prices"]], ["wfp-test"])
        self.assertEqual(response.data["prices"][0]["price_type"], "Retail")
        self.assertTrue(response.data["wfp_feed_available"])
        self.assertEqual(response.data["latest_wfp_observation"], observed_at)

    @patch("api.views.fetch_wfp_prices", side_effect=MarketDataError("upstream unavailable"))
    def test_market_feed_failure_is_visible_while_admin_prices_remain_available(self, fetch_prices):
        MarketPrice.objects.create(
            commodity="maize", market="Kalerwe", district="Kampala",
            price="1200", unit="kg", currency="UGX",
            observed_at=timezone.localdate() - timedelta(days=1),
            source_title="Market survey", source_url="https://example.test/prices",
        )

        response = self.client.get("/api/market-intelligence/")

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["wfp_feed_available"])
        self.assertEqual(len(response.data["prices"]), 1)
        self.assertIn("WFP feed is unavailable", response.data["data_note"])
        fetch_prices.assert_called_once()

    @override_settings(MARKET_INTELLIGENCE_ENABLED=False)
    @patch("api.views.fetch_wfp_prices")
    def test_market_intelligence_can_be_disabled_by_operator(self, fetch_prices):
        response = self.client.get("/api/market-intelligence/")
        self.assertEqual(response.status_code, 503)
        fetch_prices.assert_not_called()

    @patch("api.services.market_prices.requests.get")
    def test_wfp_market_feed_parses_recent_source_attributed_prices_and_caches(self, get):
        cache.delete("market-intelligence:wfp-uganda:v1")
        observed_at = timezone.localdate().isoformat()
        get.return_value.content = (
            "date,admin1,admin2,market,market_id,commodity,unit,pricetype,currency,price\n"
            f"{observed_at},Central,Kampala,Kalerwe,101,Maize (white),KG,Retail,UGX,1500\n"
            f"{observed_at},Central,Kampala,Kalerwe,101,Maize (white),KG,Wholesale,UGX,1200\n"
            f"{observed_at},Central,Kampala,Kalerwe,101,Beans,KG,Retail,UGX,0\n"
        ).encode()
        get.return_value.raise_for_status.return_value = None

        first = fetch_wfp_prices()
        second = fetch_wfp_prices()

        self.assertEqual(len(first), 2)
        self.assertEqual(first[0]["source_title"], "WFP Uganda Food Prices (HDX)")
        self.assertEqual(first[0]["district"], "Kampala")
        self.assertEqual({item["price_type"] for item in first}, {"Retail", "Wholesale"})
        self.assertEqual(first, second)
        get.assert_called_once()

    @patch("api.services.market_prices.requests.get", side_effect=__import__("requests").Timeout())
    def test_wfp_market_feed_reports_upstream_failure(self, get):
        cache.delete("market-intelligence:wfp-uganda:v1")
        with self.assertRaises(MarketDataError):
            fetch_wfp_prices()


class ClimateRiskTests(TestCase):
    def test_risk_flags_include_observed_values_and_action(self):
        observations = [
            {"values": {"PRECTOTCORR": {"value": 1.0}, "T2M": {"value": 38.0}}},
            {"values": {"PRECTOTCORR": {"value": 1.0}, "T2M": {"value": 31.0}}},
        ]
        risks = identify_climate_risks(observations, expected_days=2)["risks"]
        self.assertEqual([risk["type"] for risk in risks], ["low_rainfall", "high_temperature"])
        self.assertTrue(all(risk["level"] == "high" for risk in risks))
        self.assertTrue(all(risk["action"] for risk in risks))

    def test_incomplete_rainfall_period_is_not_screened_as_dry(self):
        result = identify_climate_risks([{"values": {"PRECTOTCORR": {"value": 0.0}}}], expected_days=30)
        self.assertFalse(result["screening_available"])
        self.assertEqual(result["risks"], [])

    @override_settings(NASA_POWER_BASE_URL="https://example.test/power")
    @patch("api.services.nasa_power.requests.get")
    def test_weather_filters_non_finite_values(self, get):
        start = date.today() - timedelta(days=3)
        day = start.strftime("%Y%m%d")
        response = Mock()
        response.json.return_value = {"properties": {"parameter": {
            "PRECTOTCORR": {day: float("inf")},
            "T2M": {day: float("nan")},
        }}}
        response.raise_for_status.return_value = None
        get.return_value = response
        result = fetch_daily_weather(0.419, 32.554, start.isoformat(), start.isoformat())
        self.assertEqual(result["observations"], [])

    @override_settings(
        OPEN_METEO_BASE_URL="https://example.test/forecast",
        OPEN_METEO_TIMEOUT=5,
    )
    @patch("api.services.open_meteo.requests.get")
    def test_live_weather_parses_and_caches_current_and_forecast_data(self, get):
        response = Mock()
        response.json.return_value = {
            "timezone": "Africa/Kampala",
            "current": {
                "time": "2026-11-17T13:00",
                "temperature_2m": 24.2,
                "relative_humidity_2m": 65,
                "apparent_temperature": 25.1,
                "precipitation": 0.0,
                "weather_code": 2,
                "wind_speed_10m": 11.2,
                "wind_direction_10m": 120,
                "cloud_cover": float("nan"),
                "is_day": 1,
            },
            "daily": {
                "time": ["2026-11-17", "2026-11-18"],
                "weather_code": [2, 61],
                "temperature_2m_max": [28.4, 26.0],
                "temperature_2m_min": [19.1, 18.8],
                "precipitation_sum": [0.0, 3.4],
                "precipitation_probability_max": [10],
                "et0_fao_evapotranspiration": [4.1, 3.8],
            },
        }
        response.raise_for_status.return_value = None
        get.return_value = response

        first = fetch_current_weather(3.1415, 35.9876)
        second = fetch_current_weather(3.1415, 35.9876)

        self.assertEqual(first["source"], "Open-Meteo")
        self.assertEqual(first["current"]["temperature_c"], 24.2)
        self.assertEqual(first["current"]["condition"], "Partly cloudy")
        self.assertTrue(first["current"]["is_day"])
        self.assertIsNone(first["current"]["cloud_cover_pct"])
        self.assertEqual(first["daily_forecast"][1]["precipitation_sum_mm"], 3.4)
        self.assertEqual(first["daily_forecast"][0]["et0_mm"], 4.1)
        self.assertIsNone(first["daily_forecast"][1]["precipitation_probability_max_pct"])
        self.assertEqual(first, second)
        self.assertEqual(get.call_args.kwargs["params"]["forecast_days"], 7)
        get.assert_called_once()

    @override_settings(OPEN_METEO_BASE_URL="https://example.test/forecast", OPEN_METEO_TIMEOUT=5)
    @patch("api.services.open_meteo.requests.get", side_effect=__import__("requests").Timeout())
    def test_live_weather_reports_provider_outage(self, get):
        with self.assertRaises(WeatherServiceError):
            fetch_current_weather(3.1416, 35.9876)

    @patch("api.views.fetch_current_weather")
    def test_current_weather_endpoint_returns_owned_farm_data(self, fetch):
        owner = User.objects.create_user(username="liveweatherowner", password="StrongPass123!")
        farm = Farm.objects.create(owner=owner, name="Kawanda", district="Wakiso", size_hectares=1, latitude=0.419, longitude=32.554)
        client = APIClient()
        client.force_authenticate(owner)
        fetch.return_value = {
            "source": "Open-Meteo",
            "data_type": "modelled_current_conditions_and_forecast",
            "current": {"temperature_c": 24.2},
            "daily_forecast": [],
        }

        response = client.get(f"/api/weather/current/?farm_id={farm.id}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["farm"]["id"], farm.id)
        self.assertEqual(response.data["current"]["temperature_c"], 24.2)
        fetch.assert_called_once()
        self.assertEqual(tuple(map(float, fetch.call_args.args)), (0.419, 32.554))

    @patch("api.views.fetch_current_weather")
    def test_current_weather_endpoint_rejects_another_users_farm(self, fetch):
        owner = User.objects.create_user(username="liveweatherowner2", password="StrongPass123!")
        farm = Farm.objects.create(owner=User.objects.create_user(username="privateweather", password="StrongPass123!"), name="Private", district="Mbale", size_hectares=1, latitude=1.1, longitude=34.2)
        client = APIClient()
        client.force_authenticate(owner)

        response = client.get(f"/api/weather/current/?farm_id={farm.id}")

        self.assertEqual(response.status_code, 403)
        fetch.assert_not_called()

class AgricultureKnowledgeTests(TestCase):
    def test_retrieval_returns_relevant_context_and_source(self):
        context = (
            "Source: Uganda extension planting guide\n"
            "Beans planting depends on locally established rainfall and soil moisture.\n\n"
            "Source: Soil handling notes\n"
            "Store harvested grain in a clean, dry, ventilated place."
        )
        retrieved, sources = retrieve_knowledge("When should beans planting begin?", context)
        self.assertIn("Beans planting", retrieved)
        self.assertEqual(sources, ["Uganda extension planting guide"])

    def test_retrieval_matches_common_word_forms_in_farmer_questions(self):
        context = (
            "Source: Rice field note\n"
            "Rice leaf yellowing should be assessed before choosing a treatment."
        )
        retrieved, sources = retrieve_knowledge("What can I use to prevent yellow leaves?", context)
        self.assertIn("Rice leaf yellowing", retrieved)
        self.assertEqual(sources, ["Rice field note"])

    def test_retrieval_ignores_generic_overlap_without_topic_support(self):
        context = "Source: Field note\nFarmers should get advice before making a decision."
        retrieved, sources = retrieve_knowledge("Why do rice leaves turn yellow?", context)
        self.assertEqual(retrieved, "")
        self.assertEqual(sources, [])

    def test_retrieval_does_not_choose_irrelevant_material(self):
        retrieved, sources = retrieve_knowledge("How to manage banana pests?", "Source: Seed guide\nRice seed storage practices.")
        self.assertEqual(retrieved, "")
        self.assertEqual(sources, [])
