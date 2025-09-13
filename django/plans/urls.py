from django.urls import path, include
from . import views

app_name = "plans"

urlpatterns = [
    # API endpoints
    path("plans/", views.get_plans, name="api-plans"),
    path("subscription/", views.get_user_subscription, name="user-subscription"),
    path("usage/", views.get_usage_stats, name="usage-stats"),
    path("payments/", views.get_payment_history, name="payment-history"),
    path("cancel/", views.cancel_subscription, name="cancel-subscription"),

    # Polar Integration URLs
    path("polar/create-checkout/", views.create_polar_checkout_session, name="polar-create-checkout"),
    path("polar/webhook/", views.polar_webhook, name="polar-webhook"),


]
