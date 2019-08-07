from account.models import Member


def user_exists(username):
    return Member.objects.all().filter(username=username).count() != 0
