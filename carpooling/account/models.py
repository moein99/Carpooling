from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import RegexValidator


# Create your models here.


class Member(AbstractUser):
    Male = "M"
    Female = "F"
    GENDERS = [
        (Male, "male"),
        (Female, "female")
    ]
    profile_picture = models.ImageField(null=True, upload_to='pictures/profile/')
    bio = models.TextField(null=True, max_length=300)
    phone_number = models.CharField(max_length=11,
                                    validators=[RegexValidator(regex=r'^\d{11}$')])
    gender = models.CharField(max_length=1, choices=GENDERS, null=True)
