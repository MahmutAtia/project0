from django.core.management.base import BaseCommand
from plans.models import Plan, Feature, PlanFeatureLimit


class Command(BaseCommand):
    help = "Create initial plans and feature limits"

    def handle(self, *args, **options):
        # Create plans
        plans_data = [
            {
                "name": "Free Plan",
                "description": "Basic features to get started",
                "price": 0,
                "billing_period": "monthly",
                "polar_product_id": "387a234b-5549-465a-9ad0-898d67e6b3fd",
                "is_free": True,
                "features": [
                    "3 AI Resumes",
                    "5 Resume Edits",
                    "5 PDF Downloads",
                    "1 Website",
                    "2 Documents",
                    "3 ATS Checks",
                ],
                "is_popular": False,
            },
            {
                "name": "Pro Plan",
                "description": "Advanced features for professionals",
                "price": 29.99,
                "billing_period": "monthly",
                "polar_product_id": "1beb3161-3fa0-4ee3-88c8-d8cc9e5225b3",
                "is_free": False,
                "features": [
                    "Unlimited Resumes",
                    "Unlimited Edits",
                    "Unlimited PDFs",
                    "Unlimited Websites",
                    "Unlimited Documents",
                    "Unlimited ATS Checks",
                    "Priority Support",
                ],
                "is_popular": True,
            },
            {
                "name": "Pro Plan (Yearly)",
                "description": "Advanced features for professionals - yearly billing",
                "price": 299.99,
                "billing_period": "yearly",
                "polar_product_id": "d6475bce-fcdc-465e-98b5-b3c5cd3379d0",
                "is_free": False,
                "features": [
                    "Unlimited Resumes",
                    "Unlimited Edits",
                    "Unlimited PDFs",
                    "Unlimited Websites",
                    "Unlimited Documents",
                    "Unlimited ATS Checks",
                    "Priority Support",
                    "2 Months Free",
                ],
                "is_popular": False,
            },
        ]

        created_plans = []
        updated_plans = []
        for plan_data in plans_data:
            plan_name = plan_data.pop("name")  # Remove name for defaults
            plan, created = Plan.objects.update_or_create(
                name=plan_name, defaults=plan_data
            )
            
            if created:
                created_plans.append(plan)
                self.stdout.write(self.style.SUCCESS(f"Created plan: {plan.name}"))
            else:
                updated_plans.append(plan)
                self.stdout.write(self.style.SUCCESS(f"Updated plan: {plan.name}"))

        # Create feature limits
        feature_limits = {
            "Free Plan": {
                "resume_generation": 3,
                "resume_section_edit": 5,
                "pdf_generation": 5,
                "website_generation": 1,
                "document_generation": 2,
                "ats_checker": 3,
            },
            "Pro Plan": {
                "resume_generation": -1,  # Unlimited
                "resume_section_edit": -1,
                "pdf_generation": -1,
                "website_generation": -1,
                "document_generation": -1,
                "ats_checker": -1,
            },
            "Pro Plan (Yearly)": {
                "resume_generation": -1,  # Unlimited
                "resume_section_edit": -1,
                "pdf_generation": -1,
                "website_generation": -1,
                "document_generation": -1,
                "ats_checker": -1,
            },
        }

        for plan_name, limits in feature_limits.items():
            try:
                plan = Plan.objects.get(name=plan_name)
                for feature_code, limit in limits.items():
                    try:
                        feature = Feature.objects.get(code=feature_code)
                        plan_limit, created = PlanFeatureLimit.objects.update_or_create(
                            plan=plan, feature=feature, defaults={"limit": limit}
                        )

                        if created:
                            self.stdout.write(
                                self.style.SUCCESS(
                                    f"Created limit for {plan.name} - {feature.name}: {limit}"
                                )
                            )
                        else:
                            self.stdout.write(
                                self.style.SUCCESS(
                                    f"Updated limit for {plan.name} - {feature.name}: {limit}"
                                )
                            )
                    except Feature.DoesNotExist:
                        self.stdout.write(
                            self.style.WARNING(f"Feature not found: {feature_code}")
                        )
            except Plan.DoesNotExist:
                self.stdout.write(self.style.WARNING(f"Plan not found: {plan_name}"))

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully created {len(created_plans)} and updated {len(updated_plans)} plans."
            )
        )
