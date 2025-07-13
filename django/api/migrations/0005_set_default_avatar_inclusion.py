# Generated migration for setting default avatar inclusion preference

from django.db import migrations


def set_default_avatar_inclusion(apps, schema_editor):
    """
    Set includeAvatarInPDF to True for all existing resumes that don't have this field
    """
    Resume = apps.get_model('api', 'Resume')
    
    for resume in Resume.objects.all():
        if resume.resume and 'personal_information' in resume.resume:
            personal_info = resume.resume['personal_information']
            if 'includeAvatarInPDF' not in personal_info:
                personal_info['includeAvatarInPDF'] = True
                resume.save()


def reverse_set_default_avatar_inclusion(apps, schema_editor):
    """
    Remove includeAvatarInPDF field from all resumes
    """
    Resume = apps.get_model('api', 'Resume')
    
    for resume in Resume.objects.all():
        if resume.resume and 'personal_information' in resume.resume:
            personal_info = resume.resume['personal_information']
            if 'includeAvatarInPDF' in personal_info:
                del personal_info['includeAvatarInPDF']
                resume.save()


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0004_userprofile'),
    ]

    operations = [
        migrations.RunPython(
            set_default_avatar_inclusion,
            reverse_set_default_avatar_inclusion,
        ),
    ]
