from elasticsearch import Elasticsearch

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
es = Elasticsearch([{'host': 'localhost', 'port': 9200}])
if not es.indices.exists(index="groups_map"):
    es.indices.create(index='groups_map', body=mappings)


def index_profile(data):
    try:
        es.index(index='prof', id=data["id"], doc_type='people', body=data, request_timeout=30)
    except:
        return


def update_profile(data):
    try:
        es.update(index='prof', id=data["id"], doc_type='people', body=data, request_timeout=30)
    except:
        return


def index_group_map(data, group_id):
        es.index(index='groups_map', id=group_id, doc_type='groups_map', body=data, request_timeout=30)



def index_group(data):
    try:
        es.index(index='group', id=data["id"], doc_type='groups', body=data, request_timeout=30)
    except:
        return
