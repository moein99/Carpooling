from django import forms

from trip.models import Trip
from dateutil.parser import parse


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
