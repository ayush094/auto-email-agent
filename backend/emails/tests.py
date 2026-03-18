from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from emails.services.email_reply_service import EmailReplyService
from emails.utils.email_reply_builder import build_fallback_reply
from emails.utils.prompts import build_messages


class GenerateEmailReplyAPITests(TestCase):
    def test_bad_request_returns_400(self):
        response = self.client.post(
            "/api/generate-reply/",
            data={"sender_name": "Ava", "tone_preference": "friendly", "company_name": "Acme"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("email_content", response.json())

    @patch("emails.services.email_reply_service.EmailReplyService._generate_with_groq")
    @patch("emails.services.email_reply_service.settings.GROQ_API_KEY", "test-key")
    def test_successful_reply_returns_200(self, mock_generate_with_groq):
        mock_generate_with_groq.return_value = "Hello Priya,\n\nThank you for your email. We will share the update shortly.\n\nBest regards,\nAcme"

        response = self.client.post(
            "/api/generate-reply/",
            data={
                "email_content": "Please share the updated contract.",
                "sender_name": "Priya",
                "tone_preference": "professional",
                "company_name": "Acme",
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "reply": "Hello Priya,\n\nThank you for your email. We will share the update shortly.\n\nBest regards,\nAcme"
            },
        )

    @patch("emails.services.email_reply_service.settings.GROQ_API_KEY", "")
    def test_local_fallback_is_used_when_groq_is_not_configured(self):
        response = self.client.post(
            "/api/generate-reply/",
            data={
                "email_content": "Can you confirm receipt of the invoice request?",
                "sender_name": "Nina",
                "tone_preference": "formal",
                "company_name": "Northwind",
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("Northwind", response.json()["reply"])
        self.assertLessEqual(len(response.json()["reply"].split()), 120)

    @patch("emails.services.email_reply_service.EmailReplyService._generate_with_groq")
    @patch("emails.services.email_reply_service.settings.GROQ_API_KEY", "test-key")
    def test_groq_failure_falls_back_to_local_reply(self, mock_generate_with_groq):
        mock_generate_with_groq.side_effect = RuntimeError("temporary upstream issue")

        response = self.client.post(
            "/api/generate-reply/",
            data={
                "email_content": "We need help with a support issue.",
                "sender_name": "Sam",
                "tone_preference": "friendly",
                "company_name": "Contoso",
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("Contoso", response.json()["reply"])

    @patch("emails.services.email_reply_service.EmailReplyService._generate_with_groq")
    @patch("emails.services.email_reply_service.settings.GROQ_API_KEY", "test-key")
    def test_quota_error_returns_429(self, mock_generate_with_groq):
        from emails.exceptions import EmailReplyQuotaExceededError

        mock_generate_with_groq.side_effect = EmailReplyQuotaExceededError("AI provider quota exceeded.")

        response = self.client.post(
            "/api/generate-reply/",
            data={
                "email_content": "Please send the proposal.",
                "sender_name": "Lena",
                "tone_preference": "professional",
                "company_name": "Acme",
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.json(), {"error": "AI provider quota exceeded."})

    def test_swagger_route_is_available(self):
        response = self.client.get(reverse("schema-swagger-ui"))

        self.assertEqual(response.status_code, 200)


class EmailReplyUtilityTests(TestCase):
    def test_build_messages_contains_required_prompt_fields(self):
        messages = build_messages(
            {
                "email_content": "Can you share the invoice?",
                "sender_name": "Jordan",
                "tone_preference": "professional",
                "company_name": "Acme",
            }
        )

        self.assertEqual(messages[0]["role"], "system")
        self.assertIn("Max 120 words", messages[0]["content"])
        self.assertIn("Personalize using sender_name", messages[0]["content"])
        self.assertIn("Jordan", messages[1]["content"])

    def test_fallback_reply_stays_within_word_limit(self):
        reply = build_fallback_reply(
            {
                "email_content": "Please provide an update on the billing issue affecting our subscription renewal.",
                "sender_name": "Jordan",
                "tone_preference": "professional",
                "company_name": "Acme",
            },
            max_words=120,
        )

        self.assertLessEqual(len(reply.split()), 120)
        self.assertTrue(reply.startswith("Hello Jordan,"))

    def test_service_trims_long_provider_reply(self):
        service = EmailReplyService()
        long_reply = "word " * 140

        trimmed = service._trim_to_word_limit(long_reply.strip(), 120)

        self.assertLessEqual(len(trimmed.split()), 120)
