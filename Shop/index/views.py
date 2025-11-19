from django.shortcuts import render

# Create your views here.
def index(request):
    return render(request, 'index2_0.html')

def service(request):
    return render(request, 'index.html')