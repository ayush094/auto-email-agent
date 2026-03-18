from rest_framework import serializers


class EmailReplyRequestSerializer(serializers.Serializer):
    TONE_CHOICES = ("professional", "friendly", "formal")

    email_content = serializers.CharField(
        allow_blank=False,
        trim_whitespace=True,
        help_text="Original inbound email content that needs a reply.",
    )
    sender_name = serializers.CharField(
        allow_blank=False,
        trim_whitespace=True,
        help_text="Name of the sender to personalize the greeting.",
    )
    tone_preference = serializers.ChoiceField(
        choices=TONE_CHOICES,
        help_text="Desired reply tone. Allowed values: professional, friendly, formal.",
    )
    company_name = serializers.CharField(
        allow_blank=False,
        trim_whitespace=True,
        help_text="Company or team name used in the email signature.",
    )


class EmailReplyResponseSerializer(serializers.Serializer):
    reply = serializers.CharField(help_text="Generated email reply in plain text.")
