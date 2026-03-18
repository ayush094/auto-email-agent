import re


def build_fallback_reply(payload, max_words=120):
    sender_name = (payload.get("sender_name") or "").strip()
    company_name = payload["company_name"].strip()
    tone = payload["tone_preference"]
    email_content = payload["email_content"].strip()

    greeting = f"Dear {sender_name}," if tone == "formal" and sender_name else (
        f"Hi {sender_name}," if tone == "friendly" and sender_name else (
            f"Hello {sender_name}," if sender_name else "Hello,"
        )
    )

    acknowledgement_map = {
        "professional": "Thank you for your email.",
        "friendly": "Thanks for reaching out.",
        "formal": "Thank you for your message.",
    }
    closing_map = {
        "professional": "Best regards,",
        "friendly": "Warm regards,",
        "formal": "Sincerely,",
    }

    body = _build_resolution_sentence(email_content, tone)
    reply = f"{greeting}\n\n{acknowledgement_map[tone]} {body}\n\n{closing_map[tone]}\n{company_name}"
    return _truncate_reply(reply, max_words=max_words)


def _build_resolution_sentence(email_content, tone):
    normalized = re.sub(r"\s+", " ", email_content).strip()
    base_response = (
        "We have reviewed your request and will address it promptly."
        if tone == "formal"
        else "We have reviewed your request and will help with the next steps right away."
        if tone == "friendly"
        else "We have reviewed your request and will assist promptly."
    )

    lowered = normalized.lower()
    if any(keyword in lowered for keyword in ("invoice", "billing", "payment", "refund")):
        return "Our billing team is reviewing the details and will share an update shortly."
    if any(keyword in lowered for keyword in ("issue", "error", "bug", "problem", "support")):
        return "Our team is looking into the issue and will follow up with a resolution as soon as possible."
    if any(keyword in lowered for keyword in ("meeting", "schedule", "call", "availability")):
        return "We will confirm the requested timing and respond with the available options shortly."
    if any(keyword in lowered for keyword in ("document", "contract", "proposal", "quote")):
        return "We will review the requested document and send the relevant details shortly."
    return base_response


def _truncate_reply(reply, max_words):
    words = reply.split()
    if len(words) <= max_words:
        return reply
    truncated = " ".join(words[:max_words]).rstrip(".,;:")
    return f"{truncated}."
