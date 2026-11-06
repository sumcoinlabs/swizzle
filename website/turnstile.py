import requests
from django.conf import settings

def turnstile_passes(request):
    if not settings.TURNSTILE_SECRET_KEY:
        # Missing token is allowed for local dev, but fail closed for public production.
        return bool(settings.DEBUG)
    response = request.POST.get("cf-turnstile-response", "")
    if not response:
        return False
    try:
        result = requests.post("https://challenges.cloudflare.com/turnstile/v0/siteverify", data={
            "secret": settings.TURNSTILE_SECRET_KEY,
            "response": response,
        }, timeout=(3, 8))
        result.raise_for_status()
        return result.json().get("success") is True
    except requests.RequestException:
        return False
