from django.shortcuts import render, redirect
from django.http import HttpResponse, Http404
from django.contrib.auth.decorators import login_required

@login_required(login_url='user:login') #redirect when user is not logged in
def file_uploader(request):
    return render(request,'include/widget/file-uploader.html')