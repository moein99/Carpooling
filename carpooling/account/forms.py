from django import forms

from account.models import Member


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
