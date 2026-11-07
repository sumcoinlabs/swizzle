from django.contrib import messages
from .decorators import customer_required
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from .forms import OrganizationForm, PressReleaseForm
from .models import Organization, PressRelease
from website.turnstile import turnstile_passes

@customer_required
@require_http_methods(["GET"])
def dashboard(request):
    organizations = Organization.objects.filter(owner=request.user).order_by("name")
    releases = PressRelease.objects.filter(organization__owner=request.user).select_related("organization").order_by("-created_at")
    return render(request, "publishers/dashboard.html", {"organizations": organizations, "releases": releases})

@customer_required
@require_http_methods(["GET", "POST"])
def create_organization(request):
    form = OrganizationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        if not turnstile_passes(request):
            form.add_error(None, "Verification failed. Please try again.")
        else:
            obj = form.save(commit=False)
            obj.owner = request.user
            obj.save()
            messages.success(request, "Company profile created. Identity review is required before publication.")
            return redirect("publishers:dashboard")
    return render(request, "publishers/create_organization.html", {"form": form})

@customer_required
@require_http_methods(["GET", "POST"])
def submit_release(request, organization_id):
    org = get_object_or_404(Organization, pk=organization_id, owner=request.user)
    form = PressReleaseForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        if not turnstile_passes(request):
            form.add_error(None, "Verification failed. Please try again.")
        else:
            release = form.save(commit=False)
            release.organization = org
            release.status = "submitted"
            release.submitted_at = timezone.now()
            release.save()
            messages.success(request, "Release submitted. Pay securely, then editorial review can proceed.")
            return redirect("publishers:dashboard")
    return render(request, "publishers/submit_release.html", {"form": form, "org": org})


@require_http_methods(["GET"])
def company_profile(request, organization_id, slug):
    from django.utils.text import slugify
    org = get_object_or_404(Organization, pk=organization_id, is_verified=True)
    if slug != slugify(org.name):
        raise Http404("No such company")
    releases = PressRelease.objects.filter(organization=org, status="published", published_page__live=True).select_related("published_page").order_by("-published_at")[:100]
    return render(request, "publishers/company_profile.html", {"org": org, "releases": releases})
