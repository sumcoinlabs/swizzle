from django.urls import path
from . import views
app_name = "billing"
urlpatterns = [
    path("release/<int:release_id>/checkout/", views.pay_release, name="pay_release"),
    path("reader/checkout/", views.subscribe_reader, name="subscribe_reader"),
    path("reader/manage/", views.manage_reader, name="manage_reader"),
    path("stripe/webhook/", views.stripe_webhook, name="stripe_webhook"),
]
