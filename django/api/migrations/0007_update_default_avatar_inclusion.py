# Generated migration to update default avatar inclusion preference to False

from django.db import migrations


def update_avatar_inclusion_default(apps, schema_editor):
    """
    Update existing resumes to have avatar inclusion set to False by default.
    This provides better privacy and professional document standards.
    """
    Resume = apps.get_model('api', 'Resume')
    
    for resume in Resume.objects.all():
        if resume.resume:
            # Check if personal_information section exists
            if 'personal_information' not in resume.resume:
                resume.resume['personal_information'] = {}
            
            # Only update if includeAvatarInPDF is not explicitly set
            if 'includeAvatarInPDF' not in resume.resume['personal_information']:
                resume.resume['personal_information']['includeAvatarInPDF'] = False
                resume.save()


def reverse_avatar_inclusion_default(apps, schema_editor):
    """
    Reverse migration - set back to True for backward compatibility
    """
    Resume = apps.get_model('api', 'Resume')
    
    for resume in Resume.objects.all():
        if (resume.resume and 
            'personal_information' in resume.resume and
            resume.resume['personal_information'].get('includeAvatarInPDF') is False):
            resume.resume['personal_information']['includeAvatarInPDF'] = True
            resume.save()


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0006_update_resume_avatar_inclusion'),
    ]

    operations = [
        migrations.RunPython(
            update_avatar_inclusion_default,
            reverse_avatar_inclusion_default,
        ),
    ]
