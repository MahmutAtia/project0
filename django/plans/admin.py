from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import Feature, Plan, PlanFeatureLimit, UserSubscription, UsageRecord, PlanPayment

@admin.register(Feature)
class FeatureAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'code']
    readonly_fields = ['created_at']

class PlanFeatureLimitInline(admin.TabularInline):
    model = PlanFeatureLimit
    extra = 1
    
    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        formset.form.base_fields['feature'].queryset = Feature.objects.filter(is_active=True)
        return formset

@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ['name', 'price', 'billing_period', 'is_active', 'is_free', 'is_popular', 'created_at']
    list_filter = ['is_active', 'is_free', 'billing_period', 'is_popular', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [PlanFeatureLimitInline]
    
    actions = ['activate_plans', 'deactivate_plans']
    
    def activate_plans(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} plans were successfully activated.')
    activate_plans.short_description = "Activate selected plans"
    
    def deactivate_plans(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} plans were successfully deactivated.')
    deactivate_plans.short_description = "Deactivate selected plans"

@admin.register(UserSubscription)
class UserSubscriptionAdmin(admin.ModelAdmin):
    list_display = ['user', 'plan', 'status', 'get_status_display', 'end_date', 'created_at']  # Changed from current_period_end
    list_filter = ['status', 'plan', 'created_at']
    search_fields = ['user__username', 'user__email', 'plan__name']
    readonly_fields = ['created_at', 'updated_at']
    
    actions = ['activate_subscriptions', 'cancel_subscriptions', 'extend_subscriptions']
    
    def get_status_display(self, obj):
        if obj.status == 'active':
            if obj.is_expired:
                color = 'orange'
                status = 'Expired'
            else:
                color = 'green'
                status = 'Active'
        elif obj.status == 'canceled':
            color = 'red'
            status = 'Canceled'
        else:
            color = 'gray'
            status = obj.get_status_display()
            
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            status
        )
    get_status_display.short_description = 'Status'
    
    def activate_subscriptions(self, request, queryset):
        updated = queryset.update(status='active')
        self.message_user(request, f'{updated} subscriptions were successfully activated.')
    activate_subscriptions.short_description = "Activate selected subscriptions"
    
    def cancel_subscriptions(self, request, queryset):
        updated = queryset.update(status='canceled')
        self.message_user(request, f'{updated} subscriptions were successfully canceled.')
    cancel_subscriptions.short_description = "Cancel selected subscriptions"
    
    def extend_subscriptions(self, request, queryset):
        from datetime import timedelta
        for subscription in queryset:
            if subscription.end_date:
                subscription.end_date += timedelta(days=30)
                subscription.save()
        self.message_user(request, f'{queryset.count()} subscriptions were extended by 30 days.')
    extend_subscriptions.short_description = "Extend selected subscriptions by 30 days"

@admin.register(PlanPayment)
class PlanPaymentAdmin(admin.ModelAdmin):
    list_display = ['user', 'plan', 'total', 'variant', 'get_status_display', 'modified', 'created']
    list_filter = ['status', 'variant', 'plan', 'created']
    search_fields = ['user__username', 'user__email', 'description']
    readonly_fields = ['created', 'modified', 'token']
    
    actions = ['mark_confirmed', 'mark_rejected']
    
    def get_status_display(self, obj):
        colors = {
            'waiting': 'orange',
            'preauth': 'blue',
            'confirmed': 'green',
            'rejected': 'red',
            'refunded': 'purple',
            'error': 'darkred',
            'input': 'gray'
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.status.upper()
        )
    get_status_display.short_description = 'Status'
    
    def mark_confirmed(self, request, queryset):
        for payment in queryset:
            if payment.status in ['waiting', 'preauth']:
                payment.change_status('confirmed')
                # Create or update subscription
                from .services import PaymentService
                try:
                    PaymentService.handle_payment_success(payment)
                except Exception as e:
                    self.message_user(request, f'Error processing payment {payment.id}: {str(e)}', level='ERROR')
        self.message_user(request, f'Selected payments were marked as confirmed.')
    mark_confirmed.short_description = "Mark selected payments as confirmed"
    
    def mark_rejected(self, request, queryset):
        for payment in queryset:
            payment.change_status('rejected')
        self.message_user(request, f'Selected payments were marked as rejected.')
    mark_rejected.short_description = "Mark selected payments as rejected"

@admin.register(UsageRecord)
class UsageRecordAdmin(admin.ModelAdmin):
    list_display = ['user', 'feature', 'count', 'period_start', 'period_end']
    list_filter = ['feature', 'period_start']
    search_fields = ['user__username', 'feature__name']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'period_start'
    
    actions = ['reset_usage']
    
    def reset_usage(self, request, queryset):
        updated = queryset.update(count=0)
        self.message_user(request, f'{updated} usage records were reset to 0.')
    reset_usage.short_description = "Reset usage count to 0"