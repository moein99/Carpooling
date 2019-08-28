from django.http import HttpResponse


class HttpResponseConflict(HttpResponse):
    status_code = 409
