from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import get_object_or_404
from search import index
from account.models import Member, Report, Mail, Comment


class SignupForm(UserCreationForm):
    class Meta:
        model = Member
        fields = (
            'username', 'email', 'password1', 'password2', 'first_name', 'last_name', 'phone_number', 'gender'
        )
        help_texts = {
            'username': None,
        }

    def save(self, commit=True):
        instance = super(SignupForm, self).save(commit=False)
        if commit:
            instance.save()
        user = get_object_or_404(Member, email=self.cleaned_data["email"])
        index.index_profile({
            "id": user.id,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name
        })
        return instance


class MailForm(forms.ModelForm):
    to = forms.CharField(max_length=30)

    class Meta:
        fields = ('message', 'to')
        model = Mail

    def clean(self):
        cleaned_data = super(MailForm, self).clean()
        check_username_validity(cleaned_data.get('to'))
        return cleaned_data


def check_username_validity(username):
    if not (5 <= len(username) <= 30):
        raise forms.ValidationError(
            "username length should be in range 5 to 30 characters"
        )


class EditProfileForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(EditProfileForm, self).__init__(*args, **kwargs)
        self.fields['bio'].required = False
        self.fields['profile_picture'].required = False

    class Meta:
        model = Member
        fields = ['first_name', 'last_name', 'phone_number', 'bio', 'profile_picture']


class ReportForm(forms.ModelForm):
    class Meta:
        model = Report
        fields = ['description']


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['message']
