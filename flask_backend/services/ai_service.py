def generate_ai_reply(sender, subject, body):
    sender_name = sender.split("@", 1)[0] if sender else "there"
    return (
        f"Hi {sender_name},\n\n"
        f"Thanks for your email about \"{subject or 'your message'}\". "
        "We received your message and will review the details shortly. "
        "If there is anything urgent you want us to prioritize, feel free to reply here.\n\n"
        "Best regards,\n"
        "Support Team"
    )
