"""Keep superuser/staff sessions out of customer publishing workflows."""
from functools import wraps
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect


def customer_required(view):
    @wraps(view)
    @login_required
    def wrapper(request, *args, **kwargs):
        if request.user.is_staff:
            return redirect("control")
        return view(request, *args, **kwargs)
    return wrapper
