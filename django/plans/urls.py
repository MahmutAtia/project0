from django.urls import path, include
from . import views

app_name = 'plans'

urlpatterns = [
    # API endpoints
    path('api/plans/', views.get_plans, name='api-plans'),
    path('subscribe/', views.subscribe_to_plan, name='subscribe'),
    path('complete-payment/', views.complete_payment, name='complete-payment'),
    path('subscription/', views.get_user_subscription, name='user-subscription'),
    path('usage/', views.get_usage_stats, name='usage-stats'),
    path('payments/', views.get_payment_history, name='payment-history'),
    path('cancel/', views.cancel_subscription, name='cancel-subscription'),
    
    # Web views
    path('', views.PlanListView.as_view(), name='plan-list'),
    
    # Payment processing URLs
    path('payment/process/<int:payment_id>/', views.payment_process, name='payment-process'),
    path('payment/success/<int:payment_id>/', views.payment_success, name='payment-success'),
    path('payment/failure/<int:payment_id>/', views.payment_failure, name='payment-failure'),
    
    # Include django-payments URLs
    path('payments/', include('payments.urls')),
]