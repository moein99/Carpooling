from django import forms

from trip.models import Trip


class TripForm(forms.ModelForm):

    class Meta:
        model = Trip
        fields = ('source', 'destination', 'is_private', 'status', 'capacity', 'start_estimation', 'end_estimation',
                  'car_provider', 'trip_description')
        exclude = ('car_provider', 'source', 'destination', 'status')
