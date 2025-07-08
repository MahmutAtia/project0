from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Plan, UserSubscription
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def assign_free_plan_on_user_creation(sender, instance, created, **kwargs):
    """
    Assigns the default free plan to a user upon creation.
    """
    if created:
        try:
            # Find the active, free plan.
            free_plan = Plan.objects.get(is_free=True, is_active=True)

            # Create the subscription for the new user.
            UserSubscription.objects.create(
                user=instance, plan=free_plan, status="active"
            )
            logger.info(f"Assigned free plan to new user: {instance.username}")
        except Plan.DoesNotExist:
            logger.error(
                "No active free plan found. Could not assign a plan to the new user."
            )
        except Exception as e:
            logger.error(f"Error assigning free plan to {instance.username}: {e}")
