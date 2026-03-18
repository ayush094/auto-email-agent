import email
from unittest import TestCase
from unittest.mock import MagicMock, patch

from services.gmail_service import GmailService


class GmailServiceTests(TestCase):
    def test_extract_body_prefers_plain_text(self):
        message = email.message.EmailMessage()
        message.set_content("Hello from Gmail")

        body = GmailService._extract_body(message)

        self.assertEqual(body, "Hello from Gmail")

    def test_build_reply_subject_prefixes_re_when_missing(self):
        self.assertEqual(GmailService._build_reply_subject("Invoice Update"), "Re: Invoice Update")

    def test_build_reply_subject_does_not_duplicate_prefix(self):
        self.assertEqual(GmailService._build_reply_subject("Re: Invoice Update"), "Re: Invoice Update")

    @patch("services.gmail_service.GmailService._send_reply")
    @patch("services.gmail_service.imaplib.IMAP4_SSL")
    def test_process_unread_emails_skips_own_email(self, mock_imap_ssl, mock_send_reply):
        email_user = "me@example.com"
        service = GmailService(email_user=email_user, email_pass="app-password")

        message = email.message.EmailMessage()
        message["From"] = email_user
        message["Subject"] = "Self message"
        message.set_content("Testing")

        imap_client = MagicMock()
        imap_client.search.return_value = ("OK", [b"1"])
        imap_client.fetch.return_value = ("OK", [(b"1", message.as_bytes())])
        imap_context = mock_imap_ssl.return_value.__enter__.return_value
        imap_context.login.return_value = "OK"
        imap_context.select.return_value = ("OK", [b""])
        imap_context.search.return_value = imap_client.search.return_value
        imap_context.fetch.return_value = imap_client.fetch.return_value

        results = service.process_unread_emails()

        self.assertEqual(results[0]["status"], "skipped_own_email")
        mock_send_reply.assert_not_called()
        imap_context.store.assert_called_once_with(b"1", "+FLAGS", "\\Seen")
