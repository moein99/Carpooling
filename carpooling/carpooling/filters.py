import logging

class RequestUserFilter(logging.Filter):
    def filter(self, record):
        if hasattr(record.request, 'user') and not record.request.user.is_anonymous:
            record.user = record.request.user.username
        else:
            record.user = 'Anonymous'
        return True

