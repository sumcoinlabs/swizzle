from django import forms
from .models import Organization, PressRelease
from newsroom.models import CATEGORIES

class OrganizationForm(forms.ModelForm):
    class Meta:
        model = Organization
        fields = ("name", "website", "ticker", "contact_name", "contact_role", "jurisdiction")

class PressReleaseForm(forms.ModelForm):
    category = forms.ChoiceField(choices=CATEGORIES)
    certification = forms.BooleanField(required=True, label="I am authorized to submit this release, and the facts are accurate.")
    class Meta:
        model = PressRelease
        fields = ("title", "summary", "body_text", "category")
        widgets = {"body_text": forms.Textarea(attrs={"rows": 14})}

    def clean_body_text(self):
        body = self.cleaned_data["body_text"].strip()
        if len(body) < 250:
            raise forms.ValidationError("Provide at least 250 characters of substantive release text.")
        return body
