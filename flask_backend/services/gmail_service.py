import email
import imaplib
import smtplib
from email.header import decode_header, make_header
from email.message import EmailMessage
from email.utils import parseaddr

from services.ai_service import generate_ai_reply


class GmailService:
    IMAP_HOST = "imap.gmail.com"
    SMTP_HOST = "smtp.gmail.com"
    SMTP_PORT = 465

    def __init__(self, email_user, email_pass):
        if not email_user or not email_pass:
            raise ValueError("EMAIL_USER and EMAIL_PASS must be configured.")
        self.email_user = email_user.strip().lower()
        self.email_pass = email_pass

    def process_unread_emails(self):
        processed = []

        with imaplib.IMAP4_SSL(self.IMAP_HOST) as imap_client:
            imap_client.login(self.email_user, self.email_pass)
            imap_client.select("INBOX")

            status, message_numbers = imap_client.search(None, "UNSEEN")
            if status != "OK":
                raise RuntimeError("Failed to fetch unread emails from Gmail.")

            for message_id in message_numbers[0].split():
                status, payload = imap_client.fetch(message_id, "(RFC822)")
                if status != "OK":
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

                reply_text = generate_ai_reply(sender_email, subject, body)
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

        return processed

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
                    return payload.decode(part.get_content_charset() or "utf-8", errors="replace").strip()
        else:
            payload = message.get_payload(decode=True) or b""
            return payload.decode(message.get_content_charset() or "utf-8", errors="replace").strip()

        return ""

    @staticmethod
    def _mark_as_read(imap_client, message_id):
        imap_client.store(message_id, "+FLAGS", "\\Seen")
