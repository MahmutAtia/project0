from rest_framework import serializers
from .models import (
    Feature,
    Plan,
    PlanFeatureLimit,
    UserSubscription,
    UsageRecord,
    PlanPayment,
)


class FeatureSerializer(serializers.ModelSerializer):
    class Meta:
        model = Feature
        fields = "__all__"


class PlanFeatureLimitSerializer(serializers.ModelSerializer):
    feature = FeatureSerializer(read_only=True)
    feature_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = PlanFeatureLimit
        fields = ["id", "feature", "feature_id", "limit"]


class PlanSerializer(serializers.ModelSerializer):
    features = PlanFeatureLimitSerializer(
        many=True, read_only=True, source="feature_limits"
    )

    class Meta:
        model = Plan
        fields = [
            "id",
            "name",
            "description",
            "price",
            "billing_period",
            "is_active",
            "is_free",
            "features",
            "is_popular",
        ]


class PlanPaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlanPayment
        fields = [
            "id",
            "total",
            "currency",
            "variant",
            "status",
            "token",
            "created",
            "modified",
        ]
        read_only_fields = ["token", "created", "modified"]


class UserSubscriptionSerializer(serializers.ModelSerializer):
    plan = PlanSerializer(read_only=True)
    is_expired = serializers.ReadOnlyField()
    latest_payment = serializers.SerializerMethodField()

    class Meta:
        model = UserSubscription
        fields = [
            "id",
            "plan",
            "status",
            "start_date",
            "end_date",
            "is_expired",
            "latest_payment",
            "created_at",
        ]

    def get_latest_payment(self, obj):
        payment = (
            PlanPayment.objects.filter(subscription=obj).order_by("-created").first()
        )
        if payment:
            return PlanPaymentSerializer(payment).data
        return None


class UsageRecordSerializer(serializers.ModelSerializer):
    feature = FeatureSerializer(read_only=True)

    class Meta:
        model = UsageRecord
        fields = ["id", "feature", "count", "period_start", "period_end"]
