from django import forms


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
