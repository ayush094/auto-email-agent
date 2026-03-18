from django.urls import path

from .views import GenerateReplyView


urlpatterns = [
    path("generate-reply/", GenerateReplyView.as_view(), name="generate-email-reply"),
]
