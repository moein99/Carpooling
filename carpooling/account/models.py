from django.contrib.auth.models import AbstractUser
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.core.validators import MaxLengthValidator, MinLengthValidator
from django.db import models


# Create your models here.


class Member(AbstractUser):
    username_validator = [UnicodeUsernameValidator, MaxLengthValidator(30), MinLengthValidator(5)] # delete validators
