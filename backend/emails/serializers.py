from rest_framework import serializers


class EmailReplyRequestSerializer(serializers.Serializer):
    TONE_CHOICES = ("professional", "friendly", "formal")

    email_content = serializers.CharField(allow_blank=False, trim_whitespace=True)
    sender_name = serializers.CharField(required=False, allow_blank=True, trim_whitespace=True)
    tone_preference = serializers.ChoiceField(choices=TONE_CHOICES)
    company_name = serializers.CharField(required=False, allow_blank=True, trim_whitespace=True)


class EmailProcessingResultSerializer(serializers.Serializer):
    sender = serializers.EmailField(help_text="Email address of the message sender.")
    subject = serializers.CharField(help_text="Decoded subject line of the original email.")
    status = serializers.CharField(help_text="Processing result, such as replied or skipped_own_email.")


class EmailProcessingResponseSerializer(serializers.Serializer):
    processed_count = serializers.IntegerField(help_text="Number of unread emails processed.")
    results = EmailProcessingResultSerializer(many=True)


class InboxEmailSerializer(serializers.Serializer):
    id = serializers.CharField(help_text="IMAP message identifier.")
    sender = serializers.CharField(help_text="Display name or email address of the sender.")
    sender_email = serializers.EmailField(help_text="Email address of the sender.")
    subject = serializers.CharField(help_text="Decoded subject line of the email.")
    preview = serializers.CharField(help_text="Short preview snippet from the email body.")
    email_content = serializers.CharField(help_text="Plain-text email body content.")
    received_at = serializers.CharField(help_text="Human-readable received date.")
    status = serializers.CharField(help_text="Dashboard status, such as received or replied.")


class InboxResponseSerializer(serializers.Serializer):
    emails = InboxEmailSerializer(many=True)


class SendReplyRequestSerializer(serializers.Serializer):
    recipient_email = serializers.EmailField(help_text="Recipient email address.")
    subject = serializers.CharField(help_text="Original subject line to reply to.")
    reply_text = serializers.CharField(help_text="Approved reply text to send.")
