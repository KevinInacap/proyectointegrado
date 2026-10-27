from django.conf import settings
from django.utils.cache import add_never_cache_headers, patch_vary_headers


class PrivateResponseMiddleware:
    """Evita reutilizar documentos o respuestas API de una cuenta anterior."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        static_prefix = '/' + settings.STATIC_URL.lstrip('/')
        if not request.path_info.startswith(static_prefix):
            add_never_cache_headers(response)
            patch_vary_headers(response, ('Cookie',))
            response['Pragma'] = 'no-cache'
        return response
