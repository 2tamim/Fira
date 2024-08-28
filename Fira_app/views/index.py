from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required

@login_required(login_url='user:login') #redirect when user is not logged in
def index(request):
    context={}
    return render(request,'index.html',{'context': context})