from django import forms

from group.models import Group, Membership


class GroupForm(forms.ModelForm):
    class Meta:
        model = Group
        fields = ['code', 'title', 'is_private', 'description', 'source_lat', 'source_lon']

    def clean_source_lat(self):
        lat = self.cleaned_data['source_lat']
        if lat is None:
            self.cleaned_data['source_lon'] = None
        return lat

    def clean_source_lon(self):
        lon = self.cleaned_data['source_lon']
        if lon is None:
            self.cleaned_data['source_lat'] = None
        return lon


class MembershipForm(forms.ModelForm):
    class Meta:
        model = Membership
        fields = ['member', 'group', 'role']

