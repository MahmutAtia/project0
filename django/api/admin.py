from django.contrib import admin
from .models import Resume, GeneratedWebsite, GeneratedDocument

admin.site.register(Resume)
admin.site.register(GeneratedWebsite)
admin.site.register(GeneratedDocument)
