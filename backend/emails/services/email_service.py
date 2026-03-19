import email
import imaplib
import re
import smtplib
from email.header import decode_header, make_header
from email.message import EmailMessage
from email.utils import parsedate_to_datetime, parseaddr

from django.conf import settings

from .ai_service import AIReplyService


class EmailServiceError(Exception):
    """Raised when IMAP or SMTP processing fails."""


class EmailService:
    IMAP_HOST = "imap.gmail.com"
    SMTP_HOST = "smtp.gmail.com"
    SMTP_PORT = 465

    def __init__(self, email_user=None, email_pass=None):
        self.email_user = (email_user or settings.EMAIL_USER or "").strip().lower()
        self.email_pass = email_pass or settings.EMAIL_PASS or ""
        self.ai_service = AIReplyService()
        if not self.email_user or not self.email_pass:
            raise EmailServiceError("EMAIL_USER and EMAIL_PASS must be configured.")

    def process_unread_emails(self):
        processed = []

        try:
            with imaplib.IMAP4_SSL(self.IMAP_HOST) as imap_client:
                imap_client.login(self.email_user, self.email_pass)
                imap_client.select("INBOX")

                status, message_numbers = imap_client.search(None, "UNSEEN")
                if status != "OK":
                    raise EmailServiceError("Failed to fetch unread emails from Gmail.")

                for message_id in message_numbers[0].split():
                    status, payload = imap_client.fetch(message_id, "(RFC822)")
                    if status != "OK" or not payload or not payload[0]:
                        continue

                    message = email.message_from_bytes(payload[0][1])
                    sender_email = parseaddr(message.get("From", ""))[1].strip().lower()
                    subject = self._decode_header_value(message.get("Subject", ""))
                    body = self._extract_body(message)

                    if sender_email == self.email_user:
                        self._mark_as_read(imap_client, message_id)
                        processed.append(
                            {
                                "sender": sender_email,
                                "subject": subject,
                                "status": "skipped_own_email",
                            }
                        )
                        continue

                    reply_text = self.ai_service.generate_reply_from_email(sender_email, subject, body)
                    self._send_reply(sender_email, subject, reply_text)
                    self._mark_as_read(imap_client, message_id)
                    processed.append(
                        {
                            "sender": sender_email,
                            "subject": subject,
                            "status": "replied",
                        }
                    )

                imap_client.close()
        except EmailServiceError:
            raise
        except Exception as exc:
            raise EmailServiceError(f"Failed to process Gmail inbox: {exc}") from exc

        return processed

    def send_approved_reply(self, recipient_email, subject, reply_text):
        recipient_email = (recipient_email or "").strip().lower()
        reply_text = (reply_text or "").strip()
        subject = (subject or "").strip()

        if not recipient_email:
            raise EmailServiceError("Recipient email is required.")
        if not reply_text:
            raise EmailServiceError("Reply text is required.")

        try:
            self._send_reply(recipient_email, subject, reply_text)
        except Exception as exc:
            raise EmailServiceError(f"Failed to send approved reply: {exc}") from exc

        return {
            "recipient_email": recipient_email,
            "subject": self._build_reply_subject(subject),
            "status": "sent",
        }

    def fetch_inbox_emails(self, limit=20):
        emails = []

        try:
            with imaplib.IMAP4_SSL(self.IMAP_HOST) as imap_client:
                imap_client.login(self.email_user, self.email_pass)
                imap_client.select("INBOX")

                status, message_numbers = imap_client.search(None, "ALL")
                if status != "OK":
                    raise EmailServiceError("Failed to fetch emails from Gmail inbox.")

                message_ids = [message_id for message_id in message_numbers[0].split() if message_id]
                for message_id in reversed(message_ids[-limit:]):
                    status, payload = imap_client.fetch(message_id, "(RFC822)")
                    if status != "OK" or not payload or not payload[0]:
                        continue

                    message = email.message_from_bytes(payload[0][1])
                    sender_raw = message.get("From", "")
                    sender_name, sender_email = parseaddr(sender_raw)
                    sender_email = sender_email.strip().lower()
                    subject = self._decode_header_value(message.get("Subject", ""))
                    body = self._extract_body(message)

                    emails.append(
                        {
                            "id": message_id.decode() if isinstance(message_id, bytes) else str(message_id),
                            "sender": self._decode_header_value(sender_name) or sender_email or "Unknown Sender",
                            "sender_email": sender_email or self.email_user,
                            "subject": subject or "No subject",
                            "preview": self._build_preview(body),
                            "email_content": body,
                            "received_at": self._format_received_at(message.get("Date", "")),
                            "status": "received",
                        }
                    )

                imap_client.close()
        except EmailServiceError:
            raise
        except Exception as exc:
            raise EmailServiceError(f"Failed to fetch Gmail inbox: {exc}") from exc

        return emails

    def _send_reply(self, recipient_email, original_subject, reply_text):
        reply_message = EmailMessage()
        reply_message["From"] = self.email_user
        reply_message["To"] = recipient_email
        reply_message["Subject"] = self._build_reply_subject(original_subject)
        reply_message.set_content(reply_text)

        with smtplib.SMTP_SSL(self.SMTP_HOST, self.SMTP_PORT) as smtp_client:
            smtp_client.login(self.email_user, self.email_pass)
            smtp_client.send_message(reply_message)

    @staticmethod
    def _build_reply_subject(subject):
        subject = (subject or "").strip()
        return subject if subject.lower().startswith("re:") else f"Re: {subject or 'Your Email'}"

    @staticmethod
    def _decode_header_value(value):
        if not value:
            return ""
        return str(make_header(decode_header(value)))

    @classmethod
    def _extract_body(cls, message):
        if message.is_multipart():
            for part in message.walk():
                content_type = part.get_content_type()
                disposition = str(part.get("Content-Disposition", ""))
                if content_type == "text/plain" and "attachment" not in disposition.lower():
                    payload = part.get_payload(decode=True) or b""
                    body = payload.decode(part.get_content_charset() or "utf-8", errors="replace").strip()
                    return cls._strip_quoted_thread(body)
        else:
            payload = message.get_payload(decode=True) or b""
            body = payload.decode(message.get_content_charset() or "utf-8", errors="replace").strip()
            return cls._strip_quoted_thread(body)

        return ""

    @staticmethod
    def _mark_as_read(imap_client, message_id):
        imap_client.store(message_id, "+FLAGS", "\\Seen")

    @staticmethod
    def _build_preview(body, max_length=120):
        normalized = " ".join((body or "").split()).strip()
        if not normalized:
            return "No preview available."
        return normalized if len(normalized) <= max_length else f"{normalized[: max_length - 1]}..."

    @staticmethod
    def _format_received_at(value):
        if not value:
            return ""

        try:
            parsed = parsedate_to_datetime(value)
        except (TypeError, ValueError, IndexError, OverflowError):
            return value

        return parsed.strftime("%d %b %Y, %I:%M %p")

    @staticmethod
    def _strip_quoted_thread(body):
        if not body:
            return ""

        lines = body.splitlines()
        cleaned_lines = []
        quote_markers = (
            re.compile(r"^On .+wrote:\s*$", re.IGNORECASE),
            re.compile(r"^From:\s+", re.IGNORECASE),
            re.compile(r"^Sent:\s+", re.IGNORECASE),
            re.compile(r"^Subject:\s+", re.IGNORECASE),
            re.compile(r"^-{2,}\s*Original Message\s*-{2,}\s*$", re.IGNORECASE),
        )

        for line in lines:
            stripped = line.strip()
            if any(pattern.match(stripped) for pattern in quote_markers):
                break
            if stripped.startswith(">"):
                break
            cleaned_lines.append(line)

        cleaned_body = "\n".join(cleaned_lines).strip()
        return cleaned_body or body.strip()
