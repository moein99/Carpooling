from django.http import HttpResponseNotAllowed


def check_request_type(original_function):
    def decorator(self, *args, **kwargs):
        type = self.request.POST.get('type', 'POST')
        if type == 'PUT':
            return self.put(*args, **kwargs)
        elif type == 'DELETE':
            return self.delete(*args, **kwargs)
        return original_function(self, *args, **kwargs)
    return decorator


def only_get_allowed(original_function):
    def decorator(request, *args, **kwargs):
        if request.method == 'GET':
            return original_function(request, *args, **kwargs)
        else:
            return HttpResponseNotAllowed()
    return decorator
