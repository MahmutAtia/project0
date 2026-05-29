from rest_framework import serializers
from .models import (
    Feature,
    Plan,
    PlanFeatureLimit,
    UserSubscription,
    UsageRecord,
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




class UsageRecordSerializer(serializers.ModelSerializer):
    feature = FeatureSerializer(read_only=True)

    class Meta:
        model = UsageRecord
        fields = ["id", "feature", "count", "period_start", "period_end"]
