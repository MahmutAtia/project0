from functools import wraps
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
import logging


logger = logging.getLogger(__name__)

def require_feature(feature_name):
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def _wrapped_view(request, *args, **kwargs):
            # Lazy import to avoid startup memory issues
            from .services import UsageService
            usage_service = UsageService()

            # Skip check for unauthenticated users (optional)
            if not request.user.is_authenticated:
                return view_func(request, *args, **kwargs)

            # Check feature limit
            limit_check = usage_service.check_feature_limit(request.user, feature_name)

            if not limit_check["allowed"]:
                return JsonResponse(
                    {
                        "error": "Feature limit exceeded",
                        "message": limit_check["message"],
                        "feature": feature_name,
                    },
                    status=403,
                )

            # Execute the view
            response = view_func(request, *args, **kwargs)

            # Record usage only if the view was successful
            if 200 <= response.status_code < 300:
                usage_service.record_feature_usage(request.user, feature_name)
                logger.info(
                    f"Feature usage recorded: {feature_name} for user {request.user.id}"
                )

            return response

        return _wrapped_view

    return decorator


def check_feature_limit(feature_code):
    """Decorator that only checks limits without recording usage"""

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return view_func(request, *args, **kwargs)

            limit_check = UsageService.check_feature_limit(request.user, feature_code)

            if not limit_check["allowed"]:
                return JsonResponse(
                    {
                        "error": "Feature limit exceeded",
                        "message": limit_check["message"],
                        "feature": feature_code,
                        "remaining": limit_check.get("remaining", 0),
                    },
                    status=403,
                )

            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator
