from django.core.management.base import BaseCommand
from plans.models import Feature


class Command(BaseCommand):
    help = "Create initial features for the application"

    def handle(self, *args, **options):
        features = [
            {
                "name": "Resume Generation",
                "code": "resume_generation",
                "description": "Generate AI-powered resumes from job descriptions",
            },
            {
                "name": "Resume Section Editing",
                "code": "resume_section_edit",
                "description": "Edit individual sections of resumes",
            },
            {
                "name": "PDF Generation",
                "code": "pdf_generation",
                "description": "Generate PDF versions of resumes",
            },
            {
                "name": "Website Generation",
                "code": "website_generation",
                "description": "Create personal portfolio websites",
            },
            {
                "name": "Document Generation",
                "code": "document_generation",
                "description": "Generate cover letters and other documents",
            },
            {
                "name": "ATS Checker",
                "code": "ats_checker",
                "description": "Check resume compatibility with ATS systems",
            },
        ]

        created_count = 0
        for feature_data in features:
            feature, created = Feature.objects.get_or_create(
                code=feature_data["code"], defaults=feature_data
            )
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f"Created feature: {feature.name}")
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f"Feature already exists: {feature.name}")
                )

        self.stdout.write(
            self.style.SUCCESS(f"Successfully created {created_count} new features")
        )
