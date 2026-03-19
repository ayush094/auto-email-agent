from django.conf import settings

from emails.exceptions import EmailReplyError, EmailReplyQuotaExceededError
from emails.utils.email_reply_builder import build_fallback_reply
from emails.utils.prompts import build_messages


class AIReplyService:
    def generate_reply(self, payload):
        normalized_payload = self._normalize_payload(payload)

        if settings.GROQ_API_KEY:
            try:
                return self._generate_with_groq(normalized_payload)
            except EmailReplyQuotaExceededError:
                raise
            except Exception:
                return build_fallback_reply(normalized_payload, max_words=settings.EMAIL_REPLY_MAX_WORDS)

        return build_fallback_reply(normalized_payload, max_words=settings.EMAIL_REPLY_MAX_WORDS)

    def generate_reply_from_email(self, sender_email, subject, body):
        sender_name = (sender_email or "").split("@", 1)[0] if sender_email else ""
        email_content = f"Subject: {subject or 'No subject'}\n\n{body or ''}".strip()
        return self.generate_reply(
            {
                "email_content": email_content,
                "sender_name": sender_name,
                "tone_preference": "professional",
                "company_name": getattr(settings, "EMAIL_REPLY_SIGNATURE_NAME", "Support Team"),
            }
        )

    def _generate_with_groq(self, payload):
        try:
            from groq import Groq
        except ImportError as exc:
            raise EmailReplyError("Groq client is not installed.") from exc

        client = Groq(api_key=settings.GROQ_API_KEY)

        try:
            response = client.chat.completions.create(
                model=settings.GROQ_MODEL,
                temperature=0.3,
                max_tokens=220,
                messages=build_messages(payload, max_words=settings.EMAIL_REPLY_MAX_WORDS),
            )
        except Exception as exc:
            status_code = getattr(exc, "status_code", None)
            if status_code == 429:
                raise EmailReplyQuotaExceededError("AI provider quota exceeded. Please try again later.") from exc
            raise

        content = response.choices[0].message.content if response.choices else ""
        reply = (content or "").strip()
        if not reply:
            raise EmailReplyError("AI provider returned an empty reply.")
        return self._trim_to_word_limit(reply, settings.EMAIL_REPLY_MAX_WORDS)

    @staticmethod
    def _normalize_payload(payload):
        return {
            "email_content": (payload.get("email_content") or "").strip(),
            "sender_name": (payload.get("sender_name") or "").strip(),
            "tone_preference": (payload.get("tone_preference") or "professional").strip(),
            "company_name": (payload.get("company_name") or getattr(settings, "EMAIL_REPLY_SIGNATURE_NAME", "Support Team")).strip(),
        }

    @staticmethod
    def _trim_to_word_limit(reply, max_words):
        words = reply.split()
        if len(words) <= max_words:
            return reply
        return " ".join(words[:max_words]).rstrip(".,;:") + "."
