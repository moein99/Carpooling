from background_task import background

import carpooling.settings.production as settings

Elastic_search = settings.Elastic_search

mappings = {
    "mappings": {
        "properties": {
            "pin": {
                "properties": {
                    "location": {
                        "type": "geo_point"

                    }
                }
            },
        }
    }
}
if not Elastic_search.indices.exists(index="group_map"):
    Elastic_search.indices.create(index='group_map', body=mappings)


@background
def index_profile(data):
    Elastic_search.index(index='prof', id=data["id"], doc_type='people', body=data, request_timeout=30)


@background
def update_profile(data, user_id):
    Elastic_search.update(index='prof', id=user_id, doc_type='people', body=data, request_timeout=30)


@background
def index_group_map(data, group_id):
    Elastic_search.index(index='group_map', id=group_id, doc_type='_doc', body=data, request_timeout=30)


@background
def index_group(data):
    Elastic_search.index(index='group', id=data["id"], doc_type='groups', body=data, request_timeout=30)
