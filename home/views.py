from django.shortcuts import render
from django.http import HttpResponse

# Create your views here.

def echo(request):
    content = request.GET.get('x', '')

    return HttpResponse(content, content_type="text/plain")
