from django.contrib import admin
from .models import Resume, GeneratedWebsite, GeneratedDocument, UserProfile,BackgroundTask

admin.site.register(Resume)
admin.site.register(GeneratedWebsite)
admin.site.register(GeneratedDocument)
admin.site.register(BackgroundTask)

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'created_at', 'updated_at', 'has_avatar']
    list_filter = ['created_at', 'updated_at']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['created_at', 'updated_at']
    
    def has_avatar(self, obj):
        return bool(obj.avatar)
    has_avatar.boolean = True
    has_avatar.short_description = 'Has Avatar'
    
    fieldsets = (
        ('User Information', {
            'fields': ('user',)
        }),
        ('Avatar', {
            'fields': ('avatar',),
            'description': 'Base64 encoded avatar image'
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
