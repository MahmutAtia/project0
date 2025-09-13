from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from decimal import Decimal
import uuid
from payments import PurchasedItem
from payments.models import BasePayment


class Feature(models.Model):
    """Represents a feature that can be limited in plans"""

    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Plan(models.Model):
    """Subscription plans"""

    BILLING_PERIODS = [
        ("monthly", "Monthly"),
        ("yearly", "Yearly"),
        ("weekly", "Weekly"),
        ("daily", "Daily"),
    ]

    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    price = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.00"))]
    )
    billing_period = models.CharField(
        max_length=20, choices=BILLING_PERIODS, default="monthly"
    )  # Changed from billing_cycle
    is_active = models.BooleanField(default=True)
    polar_product_id = models.CharField(max_length=50, blank=True, null=True, help_text="The Product ID from Polar")
    polar_price_id = models.CharField(max_length=50, blank=True, null=True, help_text="The Price ID from Polar")
    is_free = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Add these fields for frontend compatibility
    features = models.JSONField(
        default=list, blank=True
    )  # For storing feature list as JSON
    is_popular = models.BooleanField(default=False)

    class Meta:
        ordering = ["price"]

    def __str__(self):
        return f"{self.name} - ${self.price}/{self.billing_period}"


class PlanFeatureLimit(models.Model):
    """Defines limits for features in each plan"""

    plan = models.ForeignKey(
        Plan, on_delete=models.CASCADE, related_name="feature_limits"
    )
    feature = models.ForeignKey(Feature, on_delete=models.CASCADE)
    limit = models.IntegerField(validators=[MinValueValidator(-1)])  # -1 for unlimited

    class Meta:
        unique_together = ["plan", "feature"]

    def __str__(self):
        limit_str = "Unlimited" if self.limit == -1 else str(self.limit)
        return f"{self.plan.name} - {self.feature.name}: {limit_str}"


class UserSubscription(models.Model):
    """Represents a user's subscription to a plan"""

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="subscription")
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE)
    polar_subscription_id = models.CharField(max_length=100, blank=True, null=True, unique=True, help_text="The Subscription ID from Polar")
    status = models.CharField(
        max_length=20,
        choices=[
            ("active", "Active"),
            ("canceled", "Canceled"),
            ("expired", "Expired"),
            ("pending", "Pending Payment"),
            ("paused", "Paused"),
        ],
        default="active",
    )
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Add fields for better subscription management
    auto_renew = models.BooleanField(default=True)
    canceled_at = models.DateTimeField(null=True, blank=True)
    grace_period_end = models.DateTimeField(null=True, blank=True)

    class Meta:
        # Ensure only one active subscription per user
        constraints = [
            models.UniqueConstraint(
                fields=["user"],
                condition=models.Q(status="active"),
                name="unique_active_subscription_per_user",
            )
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} - {self.plan.name} ({self.status})"

    @property
    def is_expired(self):
        from django.utils import timezone

        return self.end_date and timezone.now() > self.end_date


# Using django-payments for payment handling
class PlanPayment(BasePayment):
    """Payment model using django-payments"""

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE)
    subscription = models.ForeignKey(
        UserSubscription, on_delete=models.CASCADE, null=True, blank=True
    )

    def get_failure_url(self):
        return f"/plans/payment/failure/{self.id}/"

    def get_success_url(self):
        return f"/plans/payment/success/{self.id}/"

    def get_purchased_items(self):
        return [
            PurchasedItem(
                name=f"{self.plan.name} Subscription",
                quantity=1,
                price=self.plan.price,
                currency="USD",
                sku=f"plan-{self.plan.id}",
            )
        ]


class UsageRecord(models.Model):
    """Tracks feature usage for rate limiting"""

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    feature = models.ForeignKey(Feature, on_delete=models.CASCADE)
    count = models.IntegerField(default=0)
    period_start = models.DateTimeField()
    period_end = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ["user", "feature", "period_start"]

    def __str__(self):
        return f"{self.user.username} - {self.feature.name}: {self.count}"
