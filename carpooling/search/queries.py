from search.index import es


def profile_username_name_search(data):
    query = {"bool": {"should": [
        {"wildcard": {'username': {"value": "*" + data + "*"}}},
        {"wildcard": {'first_name': {"value": "*" + data + "*"}}},
        {"wildcard": {'last_name': {"value": "*" + data + "*"}}},
    ]
    }
    }

    return es.search(index="prof", body={"query": query}, size=10)


def group_search_with_out_map(data):
    query = {"bool": {"should": [
        {"wildcard": {'title': {"value": "*" + data + "*"}}},
        {"wildcard": {'code': {"value": "*" + data + "*"}}},
        {"wildcard": {'description': {"value": "*" + data + "*"}}},
    ]
    }
    }

    return es.search(index="group", body={"query": query}, size=20)


def group_search_with_map(data):
    query = {
        "bool": {
            "must": {
                "match_all": {}
            },
            "filter": {
                "geo_distance": {
                    "distance": "12km",
                    "pin.location": {
                        "lat": data["lat"],
                        "lon": data["lon"]
                    }
                }
            }
        }
    }
    return es.search(index="group_map", body={"query": query}, size=20)
