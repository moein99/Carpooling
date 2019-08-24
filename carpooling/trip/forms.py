from dateutil.parser import parse
from django import forms
from django.contrib.gis.geos import Point
from django.db.transaction import atomic

from account.models import Mail
from trip.models import Trip, TripRequest, Companionship
from trip.utils import get_trip_score


def check_times_validity(form_data):
    try:
        start_time = parse(str(form_data['start_estimation']))
    except KeyError:
        raise forms.ValidationError('Start time is required')
    try:
        end_time = parse(str(form_data['end_estimation']))
    except KeyError:
        raise forms.ValidationError('End time is required')
    if end_time < start_time:
        raise forms.ValidationError(
            "Start time should be before end time"
        )


class TripMapForm(forms.Form):
    __POINT_X_UPPER_BOUND = 90
    __POINT_X_LOWER_BOUND = 0
    __POINT_Y_UPPER_BOUND = 180
    __POINT_Y_LOWER_BOUND = 0

    source_lat = forms.FloatField(widget=forms.HiddenInput, initial=35.7)
    source_lng = forms.FloatField(widget=forms.HiddenInput, initial=51.4)
    destination_lat = forms.FloatField(widget=forms.HiddenInput, initial=35.7)
    destination_lng = forms.FloatField(widget=forms.HiddenInput, initial=51.3)

    @classmethod
    def is_point_valid(cls, point):
        return cls.__POINT_X_LOWER_BOUND <= point.x <= cls.__POINT_X_UPPER_BOUND and \
               cls.__POINT_Y_LOWER_BOUND <= point.y <= cls.__POINT_Y_UPPER_BOUND

    def _extract_source(self):
        try:
            self.cleaned_data['source'] = Point(float(self.cleaned_data.pop('source_lat')),
                                                float(self.cleaned_data.pop('source_lng')))
            if not self.is_point_valid(self.cleaned_data['source']):
                raise ValueError()
        except (KeyError, TypeError, ValueError):
            raise forms.ValidationError('Invalid source location')

    def _extract_destination(self):
        try:
            self.cleaned_data['destination'] = Point(float(self.cleaned_data.pop('destination_lat')),
                                                     float(self.cleaned_data.pop('destination_lng')))
            if not self.is_point_valid(self.cleaned_data['destination']):
                raise ValueError()
        except (KeyError, TypeError, ValueError):
            raise forms.ValidationError('Invalid destination location')

    def clean(self):
        self._extract_source()
        self._extract_destination()
        return self.cleaned_data

    class Meta:
        fields = ['source_lat', 'source_lng', 'destination_lat', 'destination_lng']


class TripForm(forms.ModelForm):
    class Meta:
        model = Trip
        fields = ('is_private', 'people_can_join_automatically', 'capacity', 'start_estimation', 'end_estimation',
                  'trip_description')

    def clean(self):
        cleaned_data = super(TripForm, self).clean()
        check_times_validity(cleaned_data)
        self.check_capacity_validity(cleaned_data)
        self.check_description_validity(cleaned_data)
        return cleaned_data

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
        return TripMapForm.is_point_valid(point)


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
        create_new_request_set = self.cleaned_data['create_new_request_set']
        containing_set = self.cleaned_data['containing_set']
        new_request_set_title = self.cleaned_data['new_request_set_title']
        if not create_new_request_set and containing_set is None:
            raise forms.ValidationError('No set assigned to the request')
        if create_new_request_set and new_request_set_title == '':
            self.cleaned_data['new_request_set_title'] = 'No Title'
        if containing_set is not None and containing_set.closed:
            raise forms.ValidationError('Selected request set is closed')
        return self.cleaned_data

    class Meta:
        model = TripRequest
        fields = ['containing_set', 'create_new_request_set', 'new_request_set_title']


class AutomaticJoinTripForm(TripMapForm):
    start_estimation = forms.DateTimeField()
    end_estimation = forms.DateTimeField()

    def __init__(self, user=None, trip_score_threshold=None, *args, **kwargs):
        super(AutomaticJoinTripForm, self).__init__(*args, **kwargs)
        self.user = user
        self.trip_score_threshold = trip_score_threshold

    def join_a_trip_automatically(self):
        trips = Trip.get_accessible_trips_for(self.user).filter(people_can_join_automatically=True,
                                                                status=Trip.WAITING_STATUS)

        source, destination = self.cleaned_data['source'], self.cleaned_data['destination']
        trips = sorted(trips, key=lambda trip: (get_trip_score(trip, source, destination)))
        trips = filter(lambda trip: self.__is_ok_to_join(trip), trips)
        for trip in trips:
            if self.__join_if_trip_is_not_full(trip):
                return trip
        return None

    def __is_ok_to_join(self, trip):
        return self.__is_score_under_threshold(trip) and self.__time_has_conflict(trip)

    def __is_score_under_threshold(self, trip):
        source, destination = self.cleaned_data['source'], self.cleaned_data['destination']
        return get_trip_score(trip, source, destination) < self.trip_score_threshold

    def __time_has_conflict(self, trip):
        start_estimation, end_estimation = self.cleaned_data['start_estimation'], self.cleaned_data['end_estimation']
        return start_estimation < trip.end_estimation and end_estimation > trip.start_estimation

    @atomic
    def __join_if_trip_is_not_full(self, trip):
        source, destination = self.cleaned_data['source'], self.cleaned_data['destination']
        if trip.capacity > trip.passengers.count():
            Companionship.objects.create(trip=trip, member=self.user, source=source, destination=destination)
            return True
        return False

    def clean(self):
        cleaned_data = super(AutomaticJoinTripForm, self).clean()
        check_times_validity(cleaned_data)
        return cleaned_data

    class Meta(TripMapForm.Meta):
        fields = TripMapForm.Meta.fields + ['start_estimation', 'end_estimation']


class QuickMailForm(forms.ModelForm):
    class Meta:
        fields = ('message',)
        model = Mail
