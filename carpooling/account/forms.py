from django import forms

from account.models import Member


class SignupForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput())
    confirm_password = forms.CharField(widget=forms.PasswordInput())

    class Meta:
        model = Member
        fields = ('username', 'email', 'password', 'confirm_password')
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
        username = self.cleaned_data.get('username')
        if not (5 <= len(username) <= 30):
            raise forms.ValidationError(
                "username length should be in range 5 to 30 characters"
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
