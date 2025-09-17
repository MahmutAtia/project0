from django.db import migrations

from django.contrib.auth.models import User

def assign_free_plan_to_existing_users(apps, schema_editor):
    """
    Find all users that do not have a UserSubscription and assign them
    the default free plan.
    """
    User = apps.get_model('auth', 'User')
    Plan = apps.get_model('plans', 'Plan')
    UserSubscription = apps.get_model('plans', 'UserSubscription')

    try:
        # Find the single free plan you have defined.
        # Assumes you have one and only one plan where is_free=True.
        free_plan = Plan.objects.get(is_free=True)
    except Plan.DoesNotExist:
        # If there's no free plan, we can't proceed.
        # You should create one in a previous migration or via the admin panel.
        print("\nWarning: No free plan found. Skipping subscription backfill.")
        return
    except Plan.MultipleObjectsReturned:
        # If you have multiple free plans, use the first one.
        print("\nWarning: Multiple free plans found. Using the first one for backfill.")
        free_plan = Plan.objects.filter(is_free=True).first()

    # Get all users who do NOT have a related subscription.
    users_without_subscription = User.objects.filter(subscription__isnull=True)
    
    print(f"\nFound {users_without_subscription.count()} users without a subscription. Assigning free plan...")

    subs_to_create = []
    for user in users_without_subscription:
        subs_to_create.append(
            UserSubscription(
                user=user,
                plan=free_plan,
                status='active',
                auto_renew=False,
                start_date=user.date_joined # Set start date to when they joined
            )
        )
    
    # Create all the missing subscriptions in a single, efficient query.
    UserSubscription.objects.bulk_create(subs_to_create)
    
    print(f"Successfully created {len(subs_to_create)} new free subscriptions.")


class Migration(migrations.Migration):

    dependencies = [
        # Make sure this points to your LAST plans migration file before this one.
        # e.g., ('plans', '0002_auto_20250916_...'),
        ('plans', '0001_initial'), # Replace with your actual previous migration
        ('auth', '__latest__'),
    ]

    operations = [
        migrations.RunPython(assign_free_plan_to_existing_users, migrations.RunPython.noop),
    ]