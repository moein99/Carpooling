from django import forms

from account.models import Member, Mail


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
        fields = ('username', 'email', 'password', 'confirm_password')
        help_texts = {
            'username': None,
        }

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


class MailForm(forms.ModelForm):
    receiver_username = forms.CharField(max_length=30)

    class Meta:
        fields = ('text', 'receiver', 'sender', 'sent_time', 'receiver_username')
        model = Mail

        exclude = ('sender', 'sent_time', 'receiver')

    def clean(self):
        cleaned_data = super(MailForm, self).clean()
        check_username_validity(cleaned_data.get('receiver_username'))
        return cleaned_data


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
