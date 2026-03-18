from django.conf import settings

from emails.exceptions import EmailReplyError, EmailReplyQuotaExceededError
from emails.utils.email_reply_builder import build_fallback_reply
from emails.utils.prompts import build_messages


class EmailReplyService:
    def generate_reply(self, payload):
        if settings.GROQ_API_KEY:
            try:
                return self._generate_with_groq(payload)
            except EmailReplyQuotaExceededError:
                raise
            except Exception:
                return build_fallback_reply(payload, max_words=settings.EMAIL_REPLY_MAX_WORDS)

        return build_fallback_reply(payload, max_words=settings.EMAIL_REPLY_MAX_WORDS)

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
    def _trim_to_word_limit(reply, max_words):
        words = reply.split()
        if len(words) <= max_words:
            return reply
        return " ".join(words[:max_words]).rstrip(".,;:") + "."
