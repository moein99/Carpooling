from django.contrib.auth.models import AbstractUser
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.core.validators import MaxLengthValidator, MinLengthValidator
from django.db import models


class Member(AbstractUser):
    username_validator = [UnicodeUsernameValidator, MaxLengthValidator(30), MinLengthValidator(5)]


class Mail(models.Model):
    text = models.TextField()
    sender = models.ForeignKey(Member, on_delete=models.SET_NULL, related_name="outbox", null=True)
    receiver = models.ForeignKey(Member, on_delete=models.SET_NULL, related_name="inbox", null=True)
    sent_time = models.DateTimeField(auto_now_add=True)
