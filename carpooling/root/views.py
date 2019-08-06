from django.shortcuts import render


# Create your views here.
from account.models import Mail


def home_init(request):
    data = {}
    if request.user.is_authenticated:
        unread_mails = Mail.objects.filter(is_mail_seen=False, receiver=request.user).count()
        data['unread_mails'] = unread_mails
    return render(request, 'home.html', data)
