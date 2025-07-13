# Generated migration for Resume model helper methods update

from django.db import migrations


def ensure_avatar_inclusion_field(apps, schema_editor):
    """
    Ensure all existing resumes have the includeAvatarInPDF field in personal_information
    """
    Resume = apps.get_model('api', 'Resume')
    
    updated_count = 0
    for resume in Resume.objects.all():
        if resume.resume:
            # Ensure personal_information section exists
            if 'personal_information' not in resume.resume:
                resume.resume['personal_information'] = {}
            
            # Add includeAvatarInPDF if not present
            if 'includeAvatarInPDF' not in resume.resume['personal_information']:
                resume.resume['personal_information']['includeAvatarInPDF'] = True
                resume.save()
                updated_count += 1
    
    print(f"Updated {updated_count} resumes with default avatar inclusion preference")


def reverse_ensure_avatar_inclusion_field(apps, schema_editor):
    """
    Remove includeAvatarInPDF field from all resumes (reverse operation)
    """
    Resume = apps.get_model('api', 'Resume')
    
    for resume in Resume.objects.all():
        if (resume.resume and 
            'personal_information' in resume.resume and 
            'includeAvatarInPDF' in resume.resume['personal_information']):
            del resume.resume['personal_information']['includeAvatarInPDF']
            resume.save()


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0005_set_default_avatar_inclusion'),
    ]

    operations = [
        migrations.RunPython(
            ensure_avatar_inclusion_field,
            reverse_ensure_avatar_inclusion_field,
        ),
    ]
