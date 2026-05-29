from django.utils.deprecation import MiddlewareMixin

class CustomXFrameOptionsMiddleware(MiddlewareMixin):
    def process_response(self, request, response):
        # Allow framing for /site/ URLs
        if request.path.startswith('/site/'):
            response['X-Frame-Options'] = 'ALLOWALL'
        else:
            response['X-Frame-Options'] = 'ALLOWALL'
        return response