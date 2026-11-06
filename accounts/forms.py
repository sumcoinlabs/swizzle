from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model

class RegisterForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = get_user_model()
        fields = ("username",)

from django import forms
from django.contrib.auth.password_validation import validate_password

class RecoveryResetForm(forms.Form):
    username = forms.CharField(max_length=150)
    recovery_code = forms.CharField(max_length=100, strip=True)
    password1 = forms.CharField(widget=forms.PasswordInput, label="New password")
    password2 = forms.CharField(widget=forms.PasswordInput, label="Confirm new password")

    def clean(self):
        data = super().clean()
        if data.get("password1") and data.get("password1") != data.get("password2"):
            self.add_error("password2", "Passwords must match")
        if data.get("password1"):
            validate_password(data["password1"])
        return data
