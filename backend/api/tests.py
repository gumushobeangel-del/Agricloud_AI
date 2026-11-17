from datetime import date, timedelta
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Crop, Farm, FarmQuestion
from .services.nasa_power import WeatherServiceError, fetch_daily_weather
from .services.agriculture_knowledge import retrieve_knowledge
from .services.risks import identify_climate_risks

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
