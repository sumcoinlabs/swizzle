from django.contrib.auth import login, get_user_model
from django.db import transaction
from django.utils import timezone
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods
from .forms import RegisterForm, RecoveryResetForm
from .models import RecoveryCode
from website.turnstile import turnstile_passes

@require_http_methods(["GET", "POST"])
def register(request):
    if request.user.is_authenticated:
        return redirect("control" if request.user.is_staff else "publishers:dashboard")
    form = RegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        if not turnstile_passes(request):
            form.add_error(None, "Verification failed. Please try again.")
        else:
            user = form.save()
            login(request, user)
            codes = RecoveryCode.issue_codes(user)
            response = render(request, "accounts/recovery_codes.html", {"codes": codes})
            response["Cache-Control"] = "no-store"
            return response
    return render(request, "accounts/register.html", {"form": form})


@require_http_methods(["GET", "POST"])
def reset_with_recovery_code(request):
    form = RecoveryResetForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        if not turnstile_passes(request):
            form.add_error(None, "Verification failed")
        else:
            with transaction.atomic():
                user = get_user_model().objects.filter(username=form.cleaned_data["username"]).first()
                code = None
                if user:
                    code = RecoveryCode.objects.select_for_update().filter(
                        user=user, digest=RecoveryCode.digest_code(form.cleaned_data["recovery_code"]), used_at__isnull=True
                    ).first()
                if code:
                    code.used_at = timezone.now()
                    code.save(update_fields=["used_at"])
                    user.set_password(form.cleaned_data["password1"])
                    user.save(update_fields=["password"])
                    login(request, user)
                    return redirect("control" if request.user.is_staff else "publishers:dashboard")
                form.add_error(None, "Invalid username or recovery code")
    return render(request, "accounts/recovery.html", {"form": form})


@require_http_methods(["GET"])
def account_home(request):
    if not request.user.is_authenticated:
        return redirect("accounts:login")
    return redirect("control" if request.user.is_staff else "publishers:dashboard")
