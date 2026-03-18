SYSTEM_PROMPT = """You are a professional email assistant.

Write a concise and human-like reply to the email below.

Rules:
- Max 120 words.
- Use a natural tone, never robotic.
- Personalize using sender_name.
- Do not over-apologize.
- Keep it clear and actionable.
- Include a proper greeting, acknowledgement, clear response or resolution, and professional closing.
- Return plain text only.
- Do not include bullet points, markdown, placeholders, or commentary about the prompt.
- Adapt the reply to the requested tone: professional, friendly, or formal.
- Do not invent commitments that are not supported by the email context.
"""


def build_messages(payload, max_words=120):
    sender_name = payload.get("sender_name") or "there"
    tone_preference = payload["tone_preference"]
    company_name = payload["company_name"]
    email_content = payload["email_content"]

    user_prompt = f"""Email:
{email_content}

sender_name: {sender_name}
tone_preference: {tone_preference}
company_name: {company_name}
max_words: {max_words}
"""

    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]
