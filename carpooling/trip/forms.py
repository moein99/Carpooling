from dateutil.parser import parse
from django import forms

from account.models import Member
from trip.models import Trip, TripRequest, TripRequestSet


class TripForm(forms.ModelForm):
    class Meta:
        model = Trip
        fields = ('is_private', 'capacity', 'start_estimation', 'end_estimation', 'trip_description')

    def clean(self):
        cleaned_data = super(TripForm, self).clean()
        self.check_times_validity(cleaned_data)
        self.check_capacity_validity(cleaned_data)
        self.check_description_validity(cleaned_data)
        return cleaned_data

    @staticmethod
    def check_times_validity(cleaned_data):
        start_time = parse(str(cleaned_data['start_estimation']))
        end_time = parse(str(cleaned_data['end_estimation']))
        if end_time < start_time:
            raise forms.ValidationError(
                "Start time should be before end time"
            )

    @staticmethod
    def check_capacity_validity(cleaned_data):
        capacity = int(cleaned_data['capacity'])
        if not 0 < capacity < 21:
            raise forms.ValidationError(
                "Capacity should be in range 1 - 20"
            )

    @staticmethod
    def check_description_validity(cleaned_data):
        trip_description = cleaned_data['trip_description']
        if not len(trip_description) < 201:
            raise forms.ValidationError(
                "Trip description should be at max 200 characters"
            )

    @staticmethod
    def is_point_valid(point):
        if 0 <= point[0] <= 90 and 0 <= point[1] <= 180:
            return True
        else:
            return False


class TripRequestForm(forms.ModelForm):
    create_new_request_set = forms.BooleanField(required=False, initial=False)
    new_request_set_title = forms.CharField(max_length=50, required=False)

    def __init__(self, user, trip=None, *args, **kwargs):
        super(TripRequestForm, self).__init__(*args, **kwargs)
        self.user = user
        self.trip = trip
        self.fields['containing_set'].required = False
        self.fields['containing_set'].queryset = user.trip_request_sets.all()

    def clean(self):
        if not self.cleaned_data['create_new_request_set'] and self.cleaned_data['containing_set'] is None:
            raise forms.ValidationError('No set assigned to the request')
        if self.cleaned_data['create_new_request_set'] and self.cleaned_data['new_request_set_title'] == '':
            self.cleaned_data['new_request_set_title'] = 'No Title'
        if self.cleaned_data['containing_set'].closed:
            raise forms.ValidationError('Selected request set is closed')
        return self.cleaned_data

    class Meta:
        model = TripRequest
        fields = ['containing_set', 'create_new_request_set', 'new_request_set_title']
