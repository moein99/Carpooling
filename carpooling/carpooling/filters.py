import logging


class RequestUserFilter(logging.Filter):
    def filter(self, record):
        record.user = record.request.user
        return True
