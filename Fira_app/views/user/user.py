from django.core import serializers
from django.shortcuts import render, redirect
from django.http import HttpResponse, Http404,JsonResponse
from django.contrib.auth.decorators import login_required
from django.db import transaction
from ...models import Employee,SystemSetting,Regulation
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password
from django.contrib.auth import logout
from django.contrib.sessions.models import Session
import base64
import datetime

from django.utils import timezone
from django.conf import settings
from importlib import import_module
from request.models import Request
import datetime


@login_required(login_url='user:login') #redirect when user is not logged in
def change_image(request):
    MAX_IMAGE_SIZE=2000000 #2 mega byte
    data={}
    if request.method=="POST":
        try:
            employee=Employee.objects.get(user__id=request.user.id)
            data['imgage_url']=employee.get_absolute_url
            if 'image' in request.FILES:
                img=request.FILES['image']
                if(request.FILES['image'].size>MAX_IMAGE_SIZE):
                    data["message"]="حجم تصویر بیشتر از 2 مگابایت مجاز نمی باشد."
                    data["status"]="Error"
                    return JsonResponse(data)
                if str(img)[-3:].upper() not in ("JPG","PNG","GIF","ICO",):
                    data["message"]="فرمت فایل غیر مجاز می باشد."
                    data["status"]="Error"
                    return JsonResponse(data)
                employee.avatar.delete()
                employee.avatar = img
                data["message"]="تصویر با موفقیت تعویض شد"
            employee.save()
            data["src"]=employee.get_absolute_url
            data["status"]="Complete"
        except Exception as err:
            data['message']=err.args[0]
        
    return JsonResponse(data)


@login_required(login_url='user:login') #redirect when user is not logged in
def edit(request):
    data={}
    if request.method=="POST":
        try:
            user=User.objects.get(pk=request.user.id)
            if  request.POST['oldpassword']=="" or request.POST['password']=="" or request.POST['confirmpassword']=="":
                data['message']="فیلد های مربوط به گذرواژه را تکمیل نمائید"
                return JsonResponse(data)
            if request.POST["oldpassword"] and not user.check_password(request.POST['oldpassword']):
                data['message']="گذرواژه معتبر نمی باشد"
                return JsonResponse(data)
            if request.POST["password"]!=request.POST["confirmpassword"]:
                data['message']="عدم تطابق در گذرواژه"
                return JsonResponse(data)
            if request.POST["password"] and user.check_password(request.POST['oldpassword']):
                user.password=make_password(request.POST["password"])
            user.save()
            data['message']="گذرواژه جدید با موفقیت ذخیره شد. لطفا دوباره وارد شوید"
            data['redirect']="redirect"
            return JsonResponse(data)
        except Exception as err:
            data['message']=err.args[0]
        return JsonResponse(data)
    return JsonResponse(data)


@login_required(login_url='user:login') #redirect when user is not logged in
def delete_image(request):
    data={}
    try:
        employee=Employee.objects.get(user__id=request.user.id)
        data['imgage_url']=employee.get_absolute_url
        employee.avatar.delete()    
        data["message"]="تصویر با موفقیت حذف شد"
        employee.save()
        data["src"]=employee.get_absolute_url
    except Exception as err:
        data['message']=err.args[0]
    return JsonResponse(data)


@login_required(login_url='user:login') #redirect when user is not logged in
def SaveSystemSetting(request):
    data={}
    if request.method=="POST":
        system_setting=None
        try:
            system_setting=SystemSetting.objects.get(user=request.user)
        except:
            system_setting=SystemSetting()
            system_setting.user=User.objects.get(pk=request.user.id)
        try:
            if "notification_for_report" in request.POST:
                system_setting.notification_for_report = True
            else:
                system_setting.notification_for_report = False

            if "notification_for_confirm_report" in request.POST:
                system_setting.notification_for_confirm_report = True
            else:
                system_setting.notification_for_confirm_report = False
            
            if "notification_for_task_times" in request.POST:
                system_setting.notification_for_task_times = True
            else:
                system_setting.notification_for_task_times = False

            if "darkmode" in request.POST:
                system_setting.dark_mode = True
            else:
                system_setting.dark_mode = False

            if "theme_color" in request.POST:
                system_setting.theme_color = int(request.POST.get('theme_color'))
            else:
                system_setting.theme_color = False

            if "locumtenens_active" in request.POST:
                request.user.employee.organization_group.locumtenens_active = True
            else:
                request.user.employee.organization_group.locumtenens_active = False
            request.user.employee.organization_group.save()

            system_setting.save()
            data['message']="تنظیمات با موفقیت ذخیره شد"
            data['Error']=False
            return JsonResponse(data)
        except Exception as err:
            data['message']=err.args[0]
            data['Error']=True
        return JsonResponse(data)
    return JsonResponse(data)


@login_required(login_url='user:login') #redirect when user is not logged in
def ReadSystemSetting(request):
    data={}
    try:
        data["system_setting"]=serializers.serialize('json',SystemSetting.objects.filter(user=request.user))
    except Exception as err:
        data['message']=err.args[0]
    return JsonResponse(data)


@login_required(login_url='user:login') #redirect when user is not logged in
def ShowSystemSessions(request):
    context={}
    user=request.user
    user_sessions = []
    all_sessions = Session.objects.filter(expire_date__gte = datetime.datetime.now())
    for session in all_sessions:
        session_data = session.get_decoded()
        if user.pk == int(session_data.get("_auth_user_id")):
            user_sessions.append(session.pk)
    
    ips = set(list(Request.objects.filter(time__gt = datetime.datetime.now() -datetime.timedelta(days = 30)).filter(user = user).values_list('ip')))
    context["sessions"] = "شما در حال حاضر "+str(len(user_sessions))+" نشست فعال دارید" + '\n' + "آی پی های یک ماه اخیر:" + str(ips)[1:-1]
    return JsonResponse(context)


@login_required(login_url='user:login')
def ReadRegulation(request):
    data={}
    try:
        data["regulation"]=serializers.serialize('json',Regulation.objects.all())
    except Exception as err:
        data['message']=err.args[0]
    return JsonResponse(data)