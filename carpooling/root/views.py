from django.shortcuts import render_to_response


# Create your views here.

def home_init(request):
    return render_to_response('home.html')
