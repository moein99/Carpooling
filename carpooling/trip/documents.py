from django_elasticsearch_dsl import DocType, Index
from trip.models import Trip




trips = Index('trips')

@trips.doc_type
class PostDocument(DocType):
    class Meta:
        model = Trip

        fields = [
            'id',
            'source',
            'destination',
            'is_private',
            'status',
            'start_estimation',
            'end_estimation',
            'trip_description',
        ]