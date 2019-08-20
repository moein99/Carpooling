from datetime import datetime, timedelta

from django.conf import settings
from django.contrib.auth import logout
from django.utils.deprecation import MiddlewareMixin


class AutoLogout(MiddlewareMixin):
    @staticmethod
    def process_request(request):
        if not request.user.is_authenticated:
            # Can't log out if not logged in
            return

        try:
            last_touch = request.session['last_touch']
        except KeyError:
            request.session['last_touch'] = datetime.now()
            return
        if datetime.now() - last_touch > timedelta(0, settings.AUTO_LOGOUT_DELAY_IN_MINUTES * 60, 0):
            logout(request)
            try:
                del request.session['last_touch']
            except KeyError:
                pass
            return

        request.session['last_touch'] = datetime.now()
