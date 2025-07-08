from functools import wraps
from rest_framework.response import Response
from rest_framework import status
from .services import UsageService
import logging

logger = logging.getLogger(__name__)


def require_feature(feature_code):
    """Decorator to check feature limits before executing view"""

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Skip check for unauthenticated users (optional)
            if not request.user.is_authenticated:
                return view_func(request, *args, **kwargs)

            # Check feature limit
            limit_check = UsageService.check_feature_limit(request.user, feature_code)

            if not limit_check["allowed"]:
                return Response(
                    {
                        "error": "Feature limit exceeded",
                        "message": limit_check["message"],
                        "feature": feature_code,
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

            # Execute the view
            response = view_func(request, *args, **kwargs)

            # Record usage only if the view was successful
            if 200 <= response.status_code < 300:
                UsageService.record_feature_usage(request.user, feature_code)
                logger.info(
                    f"Feature usage recorded: {feature_code} for user {request.user.id}"
                )

            return response

        return wrapper

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
                return Response(
                    {
                        "error": "Feature limit exceeded",
                        "message": limit_check["message"],
                        "feature": feature_code,
                        "remaining": limit_check.get("remaining", 0),
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator
