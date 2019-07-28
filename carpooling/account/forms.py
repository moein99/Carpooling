from django import forms

from account.models import Member


class SignupForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput())
    confirm_password = forms.CharField(widget=forms.PasswordInput())

    class Meta:
        model = Member
        fields = ('username', 'email', 'password', 'confirm_password')
        widgets = {
            'password': forms.PasswordInput(),
        }
        help_texts = {
            'username': None,
        }

    def clean(self):
        password = self.cleaned_data.get("password")
        confirm_password = self.cleaned_data.get("confirm_password")
        if password != confirm_password:
            raise forms.ValidationError(
                "password and confirm_password does not match"
            )


class LoginForm(forms.ModelForm):
    class Meta:
        fields = ('username', 'password')
        model = Member
        widgets = {
            'password': forms.PasswordInput()
        }
        help_texts = {
            'username': None,
        }