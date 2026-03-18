import logging

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .exceptions import EmailReplyError, EmailReplyQuotaExceededError
from .serializers import EmailReplyRequestSerializer, EmailReplyResponseSerializer
from .services.email_reply_service import EmailReplyService

logger = logging.getLogger(__name__)


REQUEST_EXAMPLE = {
    "email_content": (
        "Hello team, I still have not received the invoice for our March subscription. "
        "Could you please send it today?"
    ),
    "sender_name": "Rahul",
    "tone_preference": "professional",
    "company_name": "Acme Support",
}

SUCCESS_RESPONSE_EXAMPLE = {
    "reply": (
        "Hello Rahul,\n\n"
        "Thank you for your email. We understand you need the March subscription invoice. "
        "Our billing team is reviewing this now and will send it to you shortly today.\n\n"
        "Best regards,\n"
        "Acme Support"
    )
}

ERROR_SCHEMA = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        "error": openapi.Schema(type=openapi.TYPE_STRING),
    },
)

REQUEST_SCHEMA = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    required=["email_content", "sender_name", "tone_preference", "company_name"],
    properties={
        "email_content": openapi.Schema(
            type=openapi.TYPE_STRING,
            description="Original inbound email content that needs a reply.",
        ),
        "sender_name": openapi.Schema(
            type=openapi.TYPE_STRING,
            description="Name of the sender to personalize the greeting.",
        ),
        "tone_preference": openapi.Schema(
            type=openapi.TYPE_STRING,
            enum=["professional", "friendly", "formal"],
            description="Desired reply tone.",
        ),
        "company_name": openapi.Schema(
            type=openapi.TYPE_STRING,
            description="Company or team name used in the email signature.",
        ),
    },
    example=REQUEST_EXAMPLE,
)

RESPONSE_SCHEMA = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        "reply": openapi.Schema(
            type=openapi.TYPE_STRING,
            description="Generated email reply in plain text.",
        ),
    },
    example=SUCCESS_RESPONSE_EXAMPLE,
)


class GenerateReplyView(APIView):
    @swagger_auto_schema(
        operation_summary="Generate an AI email reply",
        operation_description=(
            "Generates a concise email reply with a proper greeting, acknowledgement, "
            "clear response, and professional closing. The reply tone adapts to the "
            "requested style and remains within 120 words.\n\n"
            "Example request:\n"
            "{\n"
            '  "email_content": "Hello team, I still have not received the invoice for our March subscription. Could you please send it today?",\n'
            '  "sender_name": "Rahul",\n'
            '  "tone_preference": "professional",\n'
            '  "company_name": "Acme Support"\n'
            "}\n\n"
            "Example response:\n"
            "{\n"
            '  "reply": "Hello Rahul,\\n\\nThank you for your email. We understand you need the March subscription invoice. Our billing team is reviewing this now and will send it to you shortly today.\\n\\nBest regards,\\nAcme Support"\n'
            "}"
        ),
        request_body=REQUEST_SCHEMA,
        responses={
            200: openapi.Response("Reply generated successfully.", RESPONSE_SCHEMA),
            400: openapi.Response("Bad request.", ERROR_SCHEMA),
            429: openapi.Response("AI provider quota exceeded.", ERROR_SCHEMA),
            500: openapi.Response("Server error.", ERROR_SCHEMA),
        },
        tags=["Email Replies"],
    )
    def post(self, request):
        serializer = EmailReplyRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            reply = EmailReplyService().generate_reply(serializer.validated_data)
        except EmailReplyQuotaExceededError as exc:
            logger.warning("Quota exceeded while generating email reply: %s", exc)
            return Response({"error": str(exc)}, status=status.HTTP_429_TOO_MANY_REQUESTS)
        except EmailReplyError as exc:
            logger.exception("Known email reply generation error: %s", exc)
            return Response({"error": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception:
            logger.exception("Unexpected email reply generation failure.")
            return Response(
                {"error": "An unexpected server error occurred while generating the reply."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response({"reply": reply}, status=status.HTTP_200_OK)
