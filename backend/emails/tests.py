import email
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from emails.exceptions import EmailReplyError, EmailReplyQuotaExceededError
from emails.services.ai_service import AIReplyService
from emails.services.email_service import EmailService, EmailServiceError
from emails.utils.email_reply_builder import build_fallback_reply
from emails.utils.prompts import build_messages


class GenerateReplyAPITests(TestCase):
    @patch("emails.views.AIReplyService.generate_reply")
    def test_generate_reply_returns_reply_text(self, mock_generate_reply):
        mock_generate_reply.return_value = "Hello Priya,\n\nWe are checking the order status and will update you shortly.\n\nBest regards,\nAcme"

        response = self.client.post(
            "/api/generate-reply/",
            data={
                "email_content": "I haven't received my order yet.",
                "sender_name": "Priya",
                "tone_preference": "professional",
                "company_name": "Acme",
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"reply": "Hello Priya,\n\nWe are checking the order status and will update you shortly.\n\nBest regards,\nAcme"},
        )

    def test_generate_reply_validates_required_fields(self):
        response = self.client.post(
            "/api/generate-reply/",
            data={"tone_preference": "professional"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("email_content", response.json())

    @patch("emails.views.AIReplyService.generate_reply")
    def test_generate_reply_returns_429_for_quota_error(self, mock_generate_reply):
        mock_generate_reply.side_effect = EmailReplyQuotaExceededError("AI provider quota exceeded.")

        response = self.client.post(
            "/api/generate-reply/",
            data={"email_content": "Need help", "tone_preference": "professional"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.json(), {"error": "AI provider quota exceeded."})

    @patch("emails.views.EmailService")
    def test_process_unread_emails_returns_processed_results(self, mock_email_service):
        mock_email_service.return_value.process_unread_emails.return_value = [
            {"sender": "client@example.com", "subject": "Help", "status": "replied"}
        ]

        response = self.client.post("/api/process-unread-emails/", data={}, content_type="application/json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["processed_count"], 1)
        self.assertEqual(response.json()["results"][0]["status"], "replied")

    @patch("emails.views.EmailService")
    def test_process_unread_emails_returns_500_when_processing_fails(self, mock_email_service):
        mock_email_service.side_effect = EmailServiceError("EMAIL_USER and EMAIL_PASS must be configured.")

        response = self.client.post("/api/process-unread-emails/", data={}, content_type="application/json")

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json(), {"error": "EMAIL_USER and EMAIL_PASS must be configured."})

    @patch("emails.views.EmailService")
    def test_fetch_inbox_emails_returns_messages(self, mock_email_service):
        mock_email_service.return_value.fetch_inbox_emails.return_value = [
            {
                "id": "1",
                "sender": "Client",
                "sender_email": "client@example.com",
                "subject": "Help",
                "preview": "Need help with my order",
                "email_content": "Need help with my order",
                "received_at": "19 Mar 2026, 09:15 AM",
                "status": "received",
            }
        ]

        response = self.client.get("/api/inbox-emails/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["emails"][0]["sender_email"], "client@example.com")

    @patch("emails.views.EmailService")
    def test_fetch_inbox_emails_returns_500_when_fetch_fails(self, mock_email_service):
        mock_email_service.side_effect = EmailServiceError("Failed to fetch Gmail inbox: invalid credentials")

        response = self.client.get("/api/inbox-emails/")

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json(), {"error": "Failed to fetch Gmail inbox: invalid credentials"})

    @patch("emails.views.EmailService")
    def test_send_approved_reply_returns_sent_status(self, mock_email_service):
        mock_email_service.return_value.send_approved_reply.return_value = {
            "recipient_email": "client@example.com",
            "subject": "Re: Help",
            "status": "sent",
        }

        response = self.client.post(
            "/api/send-approved-reply/",
            data={
                "recipient_email": "client@example.com",
                "subject": "Help",
                "reply_text": "Hello, we are checking this for you.",
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "sent")

    @patch("emails.views.EmailService")
    def test_send_approved_reply_returns_500_when_send_fails(self, mock_email_service):
        mock_email_service.side_effect = EmailServiceError("Failed to send approved reply: SMTP error")

        response = self.client.post(
            "/api/send-approved-reply/",
            data={
                "recipient_email": "client@example.com",
                "subject": "Help",
                "reply_text": "Hello, we are checking this for you.",
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json(), {"error": "Failed to send approved reply: SMTP error"})

    def test_swagger_route_is_available(self):
        response = self.client.get(reverse("schema-swagger-ui"))

        self.assertEqual(response.status_code, 200)


class AIReplyServiceTests(TestCase):
    def test_build_messages_contains_required_prompt_fields(self):
        messages = build_messages(
            {
                "email_content": "Can you share the invoice?",
                "sender_name": "Jordan",
                "tone_preference": "professional",
                "company_name": "",
            }
        )

        self.assertEqual(messages[0]["role"], "system")
        self.assertIn("Max 120 words", messages[0]["content"])
        self.assertIn("Jordan", messages[1]["content"])
        self.assertIn("Support Team", messages[1]["content"])

    def test_fallback_reply_uses_default_signature_when_company_missing(self):
        reply = build_fallback_reply(
            {
                "email_content": "Please provide an update on the billing issue.",
                "sender_name": "Jordan",
                "tone_preference": "professional",
                "company_name": "",
            },
            max_words=120,
        )

        self.assertLessEqual(len(reply.split()), 120)
        self.assertTrue(reply.endswith("Support Team"))

    def test_fallback_reply_answers_how_are_you_message_naturally(self):
        reply = build_fallback_reply(
            {
                "email_content": "How are you?",
                "sender_name": "Jordan",
                "tone_preference": "professional",
                "company_name": "Support Team",
            },
            max_words=120,
        )

        self.assertIn("I am doing well", reply)
        self.assertNotIn("order status", reply.lower())

    def test_fallback_reply_answers_what_are_you_doing_message_contextually(self):
        reply = build_fallback_reply(
            {
                "email_content": "What are you doing?",
                "sender_name": "Jordan",
                "tone_preference": "professional",
                "company_name": "Support Team",
            },
            max_words=120,
        )

        self.assertIn("I am here to help", reply)
        self.assertNotIn("billing", reply.lower())

    def test_ai_service_trims_long_provider_reply(self):
        service = AIReplyService()
        long_reply = "word " * 140

        trimmed = service._trim_to_word_limit(long_reply.strip(), 120)

        self.assertLessEqual(len(trimmed.split()), 120)

    def test_ai_service_generates_gmail_reply_payload(self):
        with patch.object(AIReplyService, "generate_reply", return_value="reply") as mock_generate_reply:
            service = AIReplyService()
            reply = service.generate_reply_from_email("sam@example.com", "Order update", "Where is my order?")

        self.assertEqual(reply, "reply")
        payload = mock_generate_reply.call_args.args[0]
        self.assertEqual(payload["sender_name"], "sam")
        self.assertEqual(payload["tone_preference"], "professional")


class EmailServiceTests(TestCase):
    def test_extract_body_prefers_plain_text(self):
        message = email.message.EmailMessage()
        message.set_content("Hello from Gmail")

        body = EmailService._extract_body(message)

        self.assertEqual(body, "Hello from Gmail")

    def test_extract_body_removes_quoted_thread_history(self):
        message = email.message.EmailMessage()
        message.set_content(
            "How are you?\n\nOn Thu, Mar 19, 2026, 12:55 PM Demo <demo@example.com> wrote:\n> Previous reply"
        )

        body = EmailService._extract_body(message)

        self.assertEqual(body, "How are you?")

    def test_build_reply_subject_prefixes_re_when_missing(self):
        self.assertEqual(EmailService._build_reply_subject("Invoice Update"), "Re: Invoice Update")

    def test_build_reply_subject_does_not_duplicate_prefix(self):
        self.assertEqual(EmailService._build_reply_subject("Re: Invoice Update"), "Re: Invoice Update")

    @patch("emails.services.email_service.EmailService._send_reply")
    @patch("emails.services.email_service.imaplib.IMAP4_SSL")
    def test_process_unread_emails_skips_own_email(self, mock_imap_ssl, mock_send_reply):
        email_user = "me@example.com"
        service = EmailService(email_user=email_user, email_pass="app-password")

        message = email.message.EmailMessage()
        message["From"] = email_user
        message["Subject"] = "Self message"
        message.set_content("Testing")

        imap_context = mock_imap_ssl.return_value.__enter__.return_value
        imap_context.login.return_value = "OK"
        imap_context.select.return_value = ("OK", [b""])
        imap_context.search.return_value = ("OK", [b"1"])
        imap_context.fetch.return_value = ("OK", [(b"1", message.as_bytes())])

        results = service.process_unread_emails()

        self.assertEqual(results[0]["status"], "skipped_own_email")
        mock_send_reply.assert_not_called()
        imap_context.store.assert_called_once_with(b"1", "+FLAGS", "\\Seen")

    @patch("emails.services.email_service.imaplib.IMAP4_SSL")
    def test_fetch_inbox_emails_returns_recent_messages(self, mock_imap_ssl):
        service = EmailService(email_user="me@example.com", email_pass="app-password")

        first_message = email.message.EmailMessage()
        first_message["From"] = "First Sender <first@example.com>"
        first_message["Subject"] = "First"
        first_message["Date"] = "Wed, 19 Mar 2026 09:15:00 +0000"
        first_message.set_content("First body text for preview")

        second_message = email.message.EmailMessage()
        second_message["From"] = "Second Sender <second@example.com>"
        second_message["Subject"] = "Second"
        second_message["Date"] = "Wed, 19 Mar 2026 10:15:00 +0000"
        second_message.set_content("Second body text for preview")

        imap_context = mock_imap_ssl.return_value.__enter__.return_value
        imap_context.login.return_value = "OK"
        imap_context.select.return_value = ("OK", [b""])
        imap_context.search.return_value = ("OK", [b"1 2"])
        imap_context.fetch.side_effect = [
            ("OK", [(b"2", second_message.as_bytes())]),
            ("OK", [(b"1", first_message.as_bytes())]),
        ]

        emails = service.fetch_inbox_emails(limit=2)

        self.assertEqual(len(emails), 2)
        self.assertEqual(emails[0]["sender_email"], "second@example.com")
        self.assertEqual(emails[1]["sender_email"], "first@example.com")

    @patch("emails.services.email_service.EmailService._send_reply")
    def test_send_approved_reply_sends_only_after_explicit_call(self, mock_send_reply):
        service = EmailService(email_user="me@example.com", email_pass="app-password")

        result = service.send_approved_reply(
            recipient_email="client@example.com",
            subject="Help",
            reply_text="Hello, we are checking this for you.",
        )

        mock_send_reply.assert_called_once_with(
            "client@example.com",
            "Help",
            "Hello, we are checking this for you.",
        )
        self.assertEqual(result["status"], "sent")
