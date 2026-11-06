import re
from django.conf import settings

def site_context(request):
    ad_free = False
    if request.user.is_authenticated:
        from billing.models import ReaderMembership
        try:
            ad_free = request.user.reader_membership.ad_free
        except ReaderMembership.DoesNotExist:
            pass
    return {
        "brand_name": settings.SITE_NAME,
        "release_price_display": f"{settings.PRESS_RELEASE_PRICE_CENTS / 100:,.0f}" if settings.PRESS_RELEASE_PRICE_CENTS % 100 == 0 else f"{settings.PRESS_RELEASE_PRICE_CENTS / 100:,.2f}",
        "brand_tagline": settings.SITE_TAGLINE,
        "brand_language": settings.SITE_LANGUAGE,
        "brand_logo_url": settings.SITE_LOGO_URL,
        "brand_accent_color": settings.SITE_ACCENT_COLOR if re.fullmatch(r"#[0-9a-fA-F]{6}", settings.SITE_ACCENT_COLOR) else "#076dd7",
        "turnstile_site_key": settings.TURNSTILE_SITE_KEY,
        "ad_free": ad_free,
        "show_ads": bool(settings.ADSENSE_CLIENT_ID and settings.ADSENSE_SLOT_ID and not ad_free),
        "adsense_client": settings.ADSENSE_CLIENT_ID,
        "adsense_slot": settings.ADSENSE_SLOT_ID,
    }
