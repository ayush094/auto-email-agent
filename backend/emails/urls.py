from django.urls import path

from .views import fetch_inbox_emails, generate_reply, process_unread_emails, send_approved_reply


urlpatterns = [
    path("generate-reply/", generate_reply, name="generate-email-reply"),
    path("process-unread-emails/", process_unread_emails, name="process-unread-emails"),
    path("inbox-emails/", fetch_inbox_emails, name="fetch-inbox-emails"),
    path("send-approved-reply/", send_approved_reply, name="send-approved-reply"),
]
