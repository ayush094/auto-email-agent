import logging

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .exceptions import EmailReplyError, EmailReplyQuotaExceededError
from .serializers import EmailReplyRequestSerializer, SendReplyRequestSerializer
from .services.ai_service import AIReplyService
from .services.email_service import EmailService, EmailServiceError

logger = logging.getLogger(__name__)


REPLY_REQUEST_SCHEMA = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    required=["email_content", "tone_preference"],
    properties={
        "email_content": openapi.Schema(
            type=openapi.TYPE_STRING,
            default="Hi, I haven't received my order yet. Can you help?",
        ),
        "sender_name": openapi.Schema(
            type=openapi.TYPE_STRING,
            default="Priya",
        ),
        "tone_preference": openapi.Schema(
            type=openapi.TYPE_STRING,
            enum=["professional", "friendly", "formal"],
            default="professional",
        ),
        "company_name": openapi.Schema(
            type=openapi.TYPE_STRING,
            default="Acme Support",
        ),
    },
    example={
        "email_content": "Hi, I haven't received my order yet. Can you help?",
        "sender_name": "Priya",
        "tone_preference": "professional",
        "company_name": "Acme Support",
    },
)

REPLY_RESPONSE_SCHEMA = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={"reply": openapi.Schema(type=openapi.TYPE_STRING)},
    example={
        "reply": (
            "Hello Priya,\n\nThank you for your email. We are reviewing the order status "
            "and will share an update shortly.\n\nBest regards,\nAcme Support"
        )
    },
)

PROCESS_RESPONSE_SCHEMA = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        "processed_count": openapi.Schema(type=openapi.TYPE_INTEGER),
        "results": openapi.Schema(
            type=openapi.TYPE_ARRAY,
            items=openapi.Items(
                type=openapi.TYPE_OBJECT,
                properties={
                    "sender": openapi.Schema(type=openapi.TYPE_STRING),
                    "subject": openapi.Schema(type=openapi.TYPE_STRING),
                    "status": openapi.Schema(type=openapi.TYPE_STRING),
                },
            ),
        ),
    },
    example={
        "processed_count": 1,
        "results": [
            {"sender": "client@example.com", "subject": "Pricing question", "status": "replied"}
        ],
    },
)

INBOX_EMAIL_SCHEMA = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        "id": openapi.Schema(type=openapi.TYPE_STRING),
        "sender": openapi.Schema(type=openapi.TYPE_STRING),
        "sender_email": openapi.Schema(type=openapi.TYPE_STRING),
        "subject": openapi.Schema(type=openapi.TYPE_STRING),
        "preview": openapi.Schema(type=openapi.TYPE_STRING),
        "email_content": openapi.Schema(type=openapi.TYPE_STRING),
        "received_at": openapi.Schema(type=openapi.TYPE_STRING),
        "status": openapi.Schema(type=openapi.TYPE_STRING),
    },
)

INBOX_RESPONSE_SCHEMA = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        "emails": openapi.Schema(
            type=openapi.TYPE_ARRAY,
            items=INBOX_EMAIL_SCHEMA,
        )
    },
)

SEND_REPLY_REQUEST_SCHEMA = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    required=["recipient_email", "subject", "reply_text"],
    properties={
        "recipient_email": openapi.Schema(type=openapi.TYPE_STRING),
        "subject": openapi.Schema(type=openapi.TYPE_STRING),
        "reply_text": openapi.Schema(type=openapi.TYPE_STRING),
    },
)

SEND_REPLY_RESPONSE_SCHEMA = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        "recipient_email": openapi.Schema(type=openapi.TYPE_STRING),
        "subject": openapi.Schema(type=openapi.TYPE_STRING),
        "status": openapi.Schema(type=openapi.TYPE_STRING),
    },
)

ERROR_SCHEMA = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={"error": openapi.Schema(type=openapi.TYPE_STRING)},
)


@swagger_auto_schema(
    method="post",
    operation_summary="Generate an AI email reply",
    operation_description=(
        "Generates a reply from the posted email content only. No IMAP or SMTP actions are performed.\n\n"
        "Demo request body:\n"
        "{\n"
        '  "email_content": "Hi, I haven\'t received my order yet. Can you help?",\n'
        '  "sender_name": "Priya",\n'
        '  "tone_preference": "professional",\n'
        '  "company_name": "Acme Support"\n'
        "}"
    ),
    request_body=REPLY_REQUEST_SCHEMA,
    responses={
        200: openapi.Response("Reply generated successfully.", REPLY_RESPONSE_SCHEMA),
        400: openapi.Response("Invalid request.", ERROR_SCHEMA),
        429: openapi.Response("AI provider quota exceeded.", ERROR_SCHEMA),
        500: openapi.Response("Reply generation failed.", ERROR_SCHEMA),
    },
    tags=["Email Replies"],
)
@api_view(["POST"])
def generate_reply(request):
    serializer = EmailReplyRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    try:
        reply = AIReplyService().generate_reply(serializer.validated_data)
    except EmailReplyQuotaExceededError as exc:
        logger.warning("Quota exceeded while generating email reply: %s", exc)
        return Response({"error": str(exc)}, status=status.HTTP_429_TOO_MANY_REQUESTS)
    except EmailReplyError as exc:
        logger.exception("AI reply generation failed: %s", exc)
        return Response({"error": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except Exception:
        logger.exception("Unexpected AI reply generation failure.")
        return Response(
            {"error": "An unexpected server error occurred while generating the reply."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return Response({"reply": reply}, status=status.HTTP_200_OK)


@swagger_auto_schema(
    method="get",
    operation_summary="Fetch Gmail inbox messages",
    operation_description="Loads recent Gmail inbox messages for the frontend dashboard without sending replies.",
    responses={
        200: openapi.Response("Inbox emails fetched successfully.", INBOX_RESPONSE_SCHEMA),
        500: openapi.Response("Inbox fetch failed.", ERROR_SCHEMA),
    },
    tags=["Email Automation"],
)
@api_view(["GET"])
def fetch_inbox_emails(request):
    try:
        emails = EmailService().fetch_inbox_emails()
    except EmailServiceError as exc:
        logger.exception("Inbox fetch failed: %s", exc)
        return Response({"error": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except Exception:
        logger.exception("Unexpected inbox fetch failure.")
        return Response(
            {"error": "An unexpected server error occurred while fetching inbox emails."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return Response({"emails": emails}, status=status.HTTP_200_OK)


@swagger_auto_schema(
    method="post",
    operation_summary="Send an approved AI reply",
    operation_description="Sends a reviewed AI reply only after explicit user approval from the frontend.",
    request_body=SEND_REPLY_REQUEST_SCHEMA,
    responses={
        200: openapi.Response("Approved reply sent successfully.", SEND_REPLY_RESPONSE_SCHEMA),
        400: openapi.Response("Invalid request.", ERROR_SCHEMA),
        500: openapi.Response("Reply send failed.", ERROR_SCHEMA),
    },
    tags=["Email Automation"],
)
@api_view(["POST"])
def send_approved_reply(request):
    serializer = SendReplyRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    try:
        result = EmailService().send_approved_reply(**serializer.validated_data)
    except EmailServiceError as exc:
        logger.exception("Approved reply send failed: %s", exc)
        return Response({"error": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except Exception:
        logger.exception("Unexpected approved reply send failure.")
        return Response(
            {"error": "An unexpected server error occurred while sending the approved reply."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return Response(result, status=status.HTTP_200_OK)


@swagger_auto_schema(
    method="post",
    operation_summary="Process unread Gmail emails",
    operation_description=(
        "Fetches unread Gmail messages via IMAP, generates replies using the AI service, "
        "sends them via SMTP, skips self-sent mail, and marks processed emails as read."
    ),
    request_body=openapi.Schema(type=openapi.TYPE_OBJECT, properties={}, example={}),
    responses={
        200: openapi.Response("Unread emails processed successfully.", PROCESS_RESPONSE_SCHEMA),
        500: openapi.Response("Email processing failed.", ERROR_SCHEMA),
    },
    tags=["Email Automation"],
)
@api_view(["POST"])
def process_unread_emails(request):
    try:
        results = EmailService().process_unread_emails()
    except EmailServiceError as exc:
        logger.exception("Email processing failed: %s", exc)
        return Response({"error": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except Exception:
        logger.exception("Unexpected email processing failure.")
        return Response(
            {"error": "An unexpected server error occurred while processing unread emails."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return Response({"processed_count": len(results), "results": results}, status=status.HTTP_200_OK)
