import re


def build_fallback_reply(payload, max_words=120):
    sender_name = (payload.get("sender_name") or "").strip()
    company_name = (payload.get("company_name") or "Support Team").strip()
    tone = payload["tone_preference"]
    email_content = payload["email_content"].strip()

    greeting = f"Dear {sender_name}," if tone == "formal" and sender_name else (
        f"Hi {sender_name}," if tone == "friendly" and sender_name else (
            f"Hello {sender_name}," if sender_name else "Hello,"
        )
    )

    closing_map = {
        "professional": "Best regards,",
        "friendly": "Warm regards,",
        "formal": "Sincerely,",
    }

    body = _build_resolution_sentence(email_content, tone)
    reply = f"{greeting}\n\n{body}\n\n{closing_map[tone]}\n{company_name}"
    return _truncate_reply(reply, max_words=max_words)


def _build_resolution_sentence(email_content, tone):
    normalized = re.sub(r"\s+", " ", email_content).strip()
    lowered = normalized.lower()

    if _is_how_are_you_message(lowered):
        return _build_how_are_you_response(tone)
    if _is_what_are_you_doing_message(lowered):
        return _build_what_are_you_doing_response(tone)
    if _is_simple_greeting(lowered):
        return _build_greeting_response(tone)

    if any(keyword in lowered for keyword in ("invoice", "billing", "payment", "refund")):
        return (
            "Thank you for your message. We are checking the billing details and will share an update shortly."
        )
    if any(keyword in lowered for keyword in ("issue", "error", "bug", "problem", "support")):
        return (
            "Thank you for explaining the issue. We are looking into it and will follow up with a resolution as soon as possible."
        )
    if any(keyword in lowered for keyword in ("meeting", "schedule", "call", "availability")):
        return (
            "Thank you for your message. We will confirm the requested timing and share the available options shortly."
        )
    if any(keyword in lowered for keyword in ("document", "contract", "proposal", "quote")):
        return (
            "Thank you for your message. We will review the requested document and send the relevant details shortly."
        )
    if "?" in normalized:
        return _build_direct_question_response(normalized, tone)
    return _build_general_response(tone)


def _is_how_are_you_message(lowered):
    compact = lowered.strip(" ?!.,")
    return compact in {"how are you", "how are you doing", "how are you today"}


def _is_what_are_you_doing_message(lowered):
    compact = lowered.strip(" ?!.,")
    return compact in {
        "what are you doing",
        "what are you doing now",
        "what are you up to",
        "what are you doing right now",
    }


def _is_simple_greeting(lowered):
    compact = lowered.strip(" ?!.,")
    return compact in {"hi", "hello", "hey", "good morning", "good afternoon", "good evening"}


def _build_how_are_you_response(tone):
    if tone == "friendly":
        return "Thanks for asking. I am doing well and ready to help you. Please let me know what you need."
    if tone == "formal":
        return "Thank you for asking. I am doing well and would be glad to assist you. Please let me know how I may help."
    return "Thank you for asking. I am doing well and happy to help. Please let me know how I can assist you."


def _build_what_are_you_doing_response(tone):
    if tone == "friendly":
        return "I am here and ready to help with your email or request. Please share what you need and I will assist you."
    if tone == "formal":
        return "I am available to assist you with your request. Please share the details and I will be glad to help."
    return "I am here to help with your request. Please share the details and I will assist you."


def _build_greeting_response(tone):
    if tone == "friendly":
        return "Thanks for your message. I am here and ready to help whenever you are ready."
    if tone == "formal":
        return "Thank you for your message. I am available to assist you. Please let me know how I may help."
    return "Thank you for your message. I am here to help. Please let me know what you need."


def _build_direct_question_response(normalized, tone):
    if tone == "friendly":
        return "Thank you for your question. I understand what you are asking and I am happy to help. Please share any additional detail if needed so I can give you the most accurate response."
    if tone == "formal":
        return "Thank you for your question. I understand your request and will be glad to assist you. Please share any additional detail if necessary so I can respond accurately."
    return "Thank you for your question. I understand what you are asking and I am happy to help. Please share any extra detail if needed so I can respond accurately."


def _build_general_response(tone):
    if tone == "friendly":
        return "Thanks for your message. I understand your request and will help you with the next steps right away."
    if tone == "formal":
        return "Thank you for your message. I understand your request and will address it promptly."
    return "Thank you for your message. I understand your request and will assist you promptly."


def _truncate_reply(reply, max_words):
    words = reply.split()
    if len(words) <= max_words:
        return reply
    truncated = " ".join(words[:max_words]).rstrip(".,;:")
    return f"{truncated}."
