from django.shortcuts import render, redirect
from django.http import HttpResponse, Http404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from ...models import JobExperience
import datetime
from ...utilities.date_tools import ConvertToMiladi, ConvertToSolarDate,DateTimeDifference,ConvertTimeDeltaToStringTime
from django.http import JsonResponse
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.core import serializers
from ...Serializers.human_resource_serializer import JobExperienceSerializer
from rest_framework.renderers import JSONRenderer

@login_required(login_url='user:login') #redirect when user is not logged in
def Add(request,user_id):
    context={}
    try:
        if request.method == "POST":
            _user=User.objects.get(pk=user_id)
            if (_user.employee.GetEmployeeParent!=request.user.id):
                context["message"] = "شما مجوز افزودن سابقه شغلی را ندارید."
                context["status"]=False
                return  JsonResponse(context)
            job_experience=JobExperience()
            job_experience.user=User.objects.get(pk=user_id)
            if ("job_experience_organization" in request.POST and request.POST["job_experience_organization"]!=""):
                job_experience.organization=request.POST["job_experience_organization"]
            else:
                context["message"] = "فیلد نام سازمان / شرکت باید مقدار دهی شود"
                context["status"]=False
                return  JsonResponse(context)

            if ("job_experience_job_title" in request.POST and request.POST["job_experience_job_title"]!=""):
                job_experience.job_title=request.POST["job_experience_job_title"]
            else:
                context["message"] = "فیلد عنوان شغلی باید مقدار دهی شود"
                context["status"]=False
                return  JsonResponse(context)
            
            if ("job_experience_from_date" in request.POST and request.POST["job_experience_from_date"]!=""):
                job_experience.from_date=ConvertToMiladi(request.POST["job_experience_from_date"])

            if ("job_experience_to_date" in request.POST and request.POST["job_experience_to_date"]!=""):
                job_experience.to_date=ConvertToMiladi(request.POST["job_experience_to_date"])

            if ("job_experience_description" in request.POST and request.POST["job_experience_description"]!=""):
                job_experience.description=request.POST["job_experience_description"]
            
            job_experience.save()
            context["message"] = "سابقه شغلی با موفقیت ذخیره شد"
            context["status"]=True
    except Exception as ex:
        context["message"] =ex.args[0]# "بروز خطا"
        context["status"]=False
    return  JsonResponse(context)


@login_required(login_url='user:login') 
def ToList(request,user_id):
    _user=User.objects.get(pk=user_id)
    if request.user.id not in _user.employee.GetEmployeeParentSet and request.user!=_user:
        raise PermissionDenied
    data={}
    if _user.employee.GetEmployeeParent==request.user.id:
        data["direct_manager"]=True
    else:
        data["direct_manager"]=False
    job_experiences = JobExperienceSerializer(JobExperience.objects.filter(user__pk=user_id), many=True)
    data["job_experiences"]=JSONRenderer().render(job_experiences.data).decode("utf-8") 
    return JsonResponse(data)

@login_required(login_url='user:login') 
def Delete(request,job_experience_id):
    data={}
    try:
        job_experience=JobExperience.objects.get(pk=job_experience_id)
        _user=User.objects.get(pk=job_experience.user.id)
        if (_user.employee.GetEmployeeParent!=request.user.id):
            data["message"] = "شما مجوز حذف سابقه شغلی را ندارید."
            data["status"]=False
            return  JsonResponse(data)
        job_experience.delete()
        data["message"]="حذف با موفقیت انجام شد"
        data["status"]=True
    except Exception as err:
        data['message']=err.args[0]
        data["status"]=False
    return JsonResponse(data)


@login_required(login_url='user:login') 
def Detail(request,job_experience_id):
    _user=JobExperience.objects.get(pk=job_experience_id).user
    if request.user.id not in _user.employee.GetEmployeeParentSet and request.user!=_user:
        raise PermissionDenied
    data={}
    job_experience = JobExperienceSerializer(JobExperience.objects.filter(pk=job_experience_id), many=True)
    data["job_experience"]=JSONRenderer().render(job_experience.data).decode("utf-8") 
    return JsonResponse(data)

@login_required(login_url='user:login') 
def Edit(request,job_experience_id):
    context={}
    try:
        if request.method == "POST":
            
            job_experience=JobExperience.objects.get(pk=job_experience_id)
            _user=User.objects.get(pk=job_experience.user.id)
            if (_user.employee.GetEmployeeParent!=request.user.id):
                context["message"] = "شما مجوز ویرایش سابقه شغلی را ندارید."
                context["status"]=False
                return  JsonResponse(context)
            if ("job_experience_organization" in request.POST and request.POST["job_experience_organization"]!=""):
                job_experience.organization=request.POST["job_experience_organization"]
            else:
                context["message"] = "فیلد نام سازمان / شرکت باید مقدار دهی شود"
                context["status"]=False
                return  JsonResponse(context)

            if ("job_experience_job_title" in request.POST and request.POST["job_experience_job_title"]!=""):
                job_experience.job_title=request.POST["job_experience_job_title"]
            else:
                context["message"] = "فیلد عنوان شغلی باید مقدار دهی شود"
                context["status"]=False
                return  JsonResponse(context)
            
            if ("job_experience_from_date" in request.POST and request.POST["job_experience_from_date"]!=""):
                job_experience.from_date=ConvertToMiladi(request.POST["job_experience_from_date"])
            else:
                job_experience.from_date=None

            if ("job_experience_to_date" in request.POST and request.POST["job_experience_to_date"]!=""):
                job_experience.to_date=ConvertToMiladi(request.POST["job_experience_to_date"])
            else:
                job_experience.to_date=None

            if ("job_experience_description" in request.POST and request.POST["job_experience_description"]!=""):
                job_experience.description=request.POST["job_experience_description"]
            else:
                job_experience.description=""
            
            job_experience.save()
            context["message"] = "سابقه شغلی با موفقیت ویرایش شد"
            context["status"]=True
    except Exception as ex:
        context["message"] =ex.args[0]# "بروز خطا"
        context["status"]=False
    return  JsonResponse(context)
