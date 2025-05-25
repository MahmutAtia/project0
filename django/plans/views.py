from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import ListView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from payments import get_payment_model, RedirectNeeded
from payments.core import provider_factory
import json
from decimal import Decimal

from .models import Plan, UserSubscription, PlanPayment, Feature, UsageRecord
from .serializers import PlanSerializer, UserSubscriptionSerializer, PlanPaymentSerializer
from .services import PlanService, PaymentService, UsageService, SubscriptionService

Payment = get_payment_model()

class PlanListView(ListView):
    model = Plan
    template_name = 'plans/plan_list.html'
    context_object_name = 'plans'
    
    def get_queryset(self):
        return Plan.objects.filter(is_active=True).order_by('price')

@api_view(['GET'])
def get_plans(request):
    """API endpoint to get all active plans"""
    plans = Plan.objects.filter(is_active=True).order_by('price')
    plans_data = []
    
    for plan in plans:
        plans_data.append({
            'id': plan.id,
            'name': plan.name,
            'description': plan.description,
            'price': str(plan.price),
            'billing_period': plan.billing_period,
            'features': plan.features,
            'is_popular': plan.is_popular,
        })
    
    return Response(plans_data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def subscribe_to_plan(request):
    """Subscribe user to a plan with proper handling"""
    plan_id = request.data.get('plan_id')
    variant = request.data.get('variant', 'dummy')
    
    if not plan_id:
        return Response({'error': 'Plan ID is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        plan = Plan.objects.get(id=plan_id, is_active=True)
    except Plan.DoesNotExist:
        return Response({'error': 'Plan not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Check for existing active subscription to same plan
    existing_subscription = SubscriptionService.get_active_subscription(request.user)
    if existing_subscription and existing_subscription.plan.id == plan_id:
        return Response({
            'success': True,
            'message': 'You are already subscribed to this plan',
            'subscription_id': existing_subscription.id,
            'already_subscribed': True
        })
    
    # For ANY plan (free or paid), first try to reactivate recent subscription
    reactivation_result = SubscriptionService.reactivate_subscription(request.user, plan)
    
    if reactivation_result['success']:
        return Response({
            'success': True,
            'message': f'{plan.name} reactivated successfully! No new payment required.',
            'subscription_id': reactivation_result['subscription'].id,
            'reactivated': True
        })
    
    # If no reactivation possible, handle new subscription
    if plan.is_free:
        # Create new free subscription
        try:
            subscription = PlanService.create_subscription(request.user, plan)
            return Response({
                'success': True,
                'message': f'Free plan activated successfully',
                'subscription_id': subscription.id
            })
        except Exception as e:
            return Response({
                'error': f'Failed to activate free plan: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    # For paid plans, create payment only if no reactivation
    try:
        # Create payment for paid plans
        payment = PaymentService.create_payment(
            user=request.user,
            plan=plan,
            variant=variant
        )
        
        # For dummy payments, process immediately
        if variant == 'dummy':
            payment.change_status('confirmed')
            subscription = PaymentService.handle_payment_success(payment)
            
            return Response({
                'success': True,
                'message': f'Successfully subscribed to {plan.name}!',
                'subscription_id': subscription.id,
                'payment_id': payment.id
            })
        else:
            return Response({
                'payment_id': payment.id,
                'payment_url': f'/plans/payment/process/{payment.id}/',
                'message': 'Payment created. Please complete payment.'
            })
            
    except Exception as e:
        return Response({
            'error': f'Subscription failed: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cancel_subscription(request):
    """Cancel user's current subscription with options"""
    immediate = request.data.get('immediate', False)
    
    result = SubscriptionService.cancel_subscription(request.user, immediate)
    
    if result['success']:
        return Response(result)
    else:
        return Response({
            'error': result['message']
        }, status=status.HTTP_404_NOT_FOUND)



@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_subscription(request):
    """Get current user's subscription details with proper status"""
    subscription = SubscriptionService.get_active_subscription(request.user)
    
    if subscription:
        # Determine actual subscription state
        is_canceling = subscription.is_in_grace_period if hasattr(subscription, 'is_in_grace_period') else (
            subscription.canceled_at is not None and not subscription.auto_renew
        )
        
        return Response({
            'has_subscription': True,
            'plan': {
                'id': subscription.plan.id,
                'name': subscription.plan.name,
                'description': subscription.plan.description,
                'price': str(subscription.plan.price),
                'billing_period': subscription.plan.billing_period,
                'features': subscription.plan.features,
            },
            'start_date': subscription.start_date,
            'end_date': subscription.end_date,
            'is_active': subscription.status == 'active',
            'auto_renew': subscription.auto_renew,
            'canceled_at': subscription.canceled_at,
            'is_canceling': is_canceling,
            'days_remaining': subscription.days_remaining if hasattr(subscription, 'days_remaining') else 0,
            'status': subscription.status,
        })
    else:
        return Response({
            'has_subscription': False,
            'plan': None
        })
        
        
        
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def complete_payment(request):
    """Complete a payment"""
    payment_id = request.data.get('payment_id')
    
    if not payment_id:
        return Response({'error': 'Payment ID is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        payment = PlanPayment.objects.get(id=payment_id, user=request.user)
        
        # Mark payment as confirmed
        payment.change_status('confirmed')
        
        # Create subscription
        subscription = PaymentService.handle_payment_success(payment)
        
        return Response({
            'message': 'Payment completed successfully',
            'subscription_id': subscription.id
        })
        
    except PlanPayment.DoesNotExist:
        return Response({'error': 'Payment not found'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_usage_stats(request):
    """Get user's current usage statistics"""
    user = request.user
    plan = PlanService.get_user_plan(user)
    
    if not plan:
        return Response({
            'error': 'No active subscription found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    features = Feature.objects.filter(is_active=True)
    usage_stats = []
    
    # Get current period dates
    start_date, end_date = UsageService.get_current_period_dates(plan.billing_period)
    
    for feature in features:
        # Get the feature limit for this plan
        try:
            plan_limit = plan.feature_limits.get(feature=feature)
            limit = plan_limit.limit
        except:
            limit = 0
        
        # Get current usage for this period
        try:
            usage_record = UsageRecord.objects.get(
                user=user,
                feature=feature,
                period_start=start_date
            )
            used = usage_record.count
        except UsageRecord.DoesNotExist:
            used = 0
        
        # Calculate remaining
        if limit == -1:  # Unlimited
            remaining = -1
            unlimited = True
        else:
            remaining = max(0, limit - used)
            unlimited = False
        
        usage_stats.append({
            'feature': feature.name,
            'feature_code': feature.code,
            'used': used,
            'limit': limit,
            'remaining': remaining,
            'unlimited': unlimited
        })
    
    return Response({
        'plan': plan.name,
        'usage_stats': usage_stats,
        'current_period': {
            'start': start_date,
            'end': end_date
        }
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_payment_history(request):
    """Get user's payment history"""
    payments = PlanPayment.objects.filter(user=request.user).order_by('-created')
    serializer = PlanPaymentSerializer(payments, many=True)
    return Response(serializer.data)

# Payment processing views
@login_required
def payment_process(request, payment_id):
    """Process payment through the selected provider"""
    payment = get_object_or_404(PlanPayment, id=payment_id)
    
    try:
        form = payment.get_form(data=request.POST or None)
        if form.is_valid():
            form.save()
            return redirect('plans:payment-success', payment_id=payment.id)
    except RedirectNeeded as redirect_to:
        return redirect(str(redirect_to))
    
    return render(request, 'plans/payment_form.html', {'form': form, 'payment': payment})

@login_required
def payment_success(request, payment_id):
    """Handle successful payment"""
    payment = get_object_or_404(PlanPayment, id=payment_id)
    
    if payment.status == 'confirmed':
        # Create or update subscription
        subscription = PaymentService.handle_payment_success(payment)
    
    return render(request, 'plans/payment_success.html', {'payment': payment})

@login_required
def payment_failure(request, payment_id):
    """Handle failed payment"""
    payment = get_object_or_404(PlanPayment, id=payment_id)
    return render(request, 'plans/payment_failure.html', {'payment': payment})

# Test endpoint for recording usage manually
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def test_usage_recording(request):
    """Test endpoint to record usage manually"""
    feature_code = request.data.get('feature_code')
    if not feature_code:
        return Response({'error': 'feature_code required'})
    
    success = UsageService.record_feature_usage(request.user, feature_code)
    
    if success:
        return Response({'message': f'Usage recorded for {feature_code}'})
    else:
        return Response({'error': 'Failed to record usage'})