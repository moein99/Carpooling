from django import forms
from group.models import Group


class GroupForm(forms.ModelForm):
    class Meta:
        model = Group
        fields = ['code', 'title', 'is_private', 'description']

    def __init__(self, *args, **kwargs):
        super(GroupForm, self).__init__(*args, **kwargs)
        self.fields['description'].required = False
        self.fields['is_private'].required = False
