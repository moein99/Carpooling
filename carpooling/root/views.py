from django.shortcuts import render


# Create your views here.

def home_init(request):
    return render(request, 'home.html', {})
