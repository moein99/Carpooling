from django import forms
from django.contrib.auth import authenticate

from account.models import Member


class ForgotPasswordForm(forms.Form):
    email_or_username = forms.CharField(max_length=100,
                                        widget=forms.TextInput(attrs={'placeholder': 'Username or Email'}))

    def clean(self):
        return self.cleaned_data


class ResetPasswordForm(forms.Form):
    certificate = forms.CharField(max_length=32, widget=forms.HiddenInput())
    password = forms.CharField(max_length=128, widget=forms.PasswordInput())
    confirm_password = forms.CharField(max_length=128, widget=forms.PasswordInput())

    class Meta:
        fields = ['certificate', 'password']

    def clean(self):
        cleaned_data = super(ResetPasswordForm, self).clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')

        if password != confirm_password:
            raise forms.ValidationError('password and confirm_password does not match')
        return cleaned_data


class SignupForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput())
    confirm_password = forms.CharField(widget=forms.PasswordInput())

    class Meta:
        model = Member
        fields = (
            'username', 'email', 'password', 'confirm_password', 'first_name', 'last_name', 'phone_number', 'gender')
        help_texts = {
            'username': None,
        }

    def __init__(self, *args, **kwargs):
        super(SignupForm, self).__init__(*args, **kwargs)
        self.fields['gender'].required = False

    def clean(self):
        cleaned_data = super(SignupForm, self).clean()
        password = self.cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")
        username = cleaned_data.get('username')
        check_passwords_equality(password, confirm_password)
        check_username_validity(username)
        return cleaned_data


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


def check_passwords_equality(password, confirm_password):
    if password != confirm_password:
        raise forms.ValidationError(
            "password and confirm_password does not match"
        )


def check_username_validity(username):
    if not (5 <= len(username) <= 30):
        raise forms.ValidationError(
            "username length should be in range 5 to 30 characters"
        )


class EditProfileForm(forms.ModelForm):
    class Meta:
        model = Member
        fields = ['first_name', 'last_name', 'phone_number', 'bio', 'profile_picture']

    def __init__(self, *args, **kwargs):
        super(EditProfileForm, self).__init__(*args, **kwargs)
        # self.fields['profile_picture'].required = Falss
        self.fields['bio'].required = False


class ChangePasswordForm(forms.Form):
    username = forms.CharField(max_length=150, widget=forms.HiddenInput())
    old_password = forms.CharField(max_length=128, widget=forms.PasswordInput())
    password = forms.CharField(max_length=128, widget=forms.PasswordInput())
    confirm_password = forms.CharField(max_length=128, widget=forms.PasswordInput())

    class Meta:
        fields = ['username', 'old_password', 'password', 'confirm_password']

    def clean(self):
        cleaned_data = super(ChangePasswordForm, self).clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')
        username = cleaned_data.get('username')
        old_password = cleaned_data.get('old_password')
        if password != confirm_password:
            raise forms.ValidationError('password and confirm_password does not match')
        user = authenticate(username=username, password=old_password)
        if not user:
            raise forms.ValidationError('Wrong password')
        return cleaned_data

