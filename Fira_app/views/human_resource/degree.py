from django.shortcuts import render, redirect
from django.http import HttpResponse, Http404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from ...models import Degree
import datetime
from ...utilities.date_tools import ConvertToMiladi, ConvertToSolarDate,DateTimeDifference,ConvertTimeDeltaToStringTime
from django.http import JsonResponse
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from ...Serializers.human_resource_serializer import DegreeSerializer
from rest_framework.renderers import JSONRenderer

@login_required(login_url='user:login') #redirect when user is not logged in
def Add(request,user_id):
    context={}
    try:
        if request.method == "POST":
            _user=User.objects.get(pk=user_id)
            if (_user.employee.GetEmployeeParent!=request.user.id):
                context["message"] = "شما مجوز افزودن مقطع تحصیلی را ندارید."
                context["status"]=False
                return  JsonResponse(context)
            degree=Degree()
            degree.user=User.objects.get(pk=user_id)
            if ("degree_level" in request.POST and int(request.POST["degree_level"])>0):
                degree.level=int(request.POST["degree_level"])
            else:
                context["message"] = "فیلد مقطع تحصیلی باید مقدار دهی شود"
                context["status"]=False
                return  JsonResponse(context)
            if ("university_name" in request.POST and request.POST["university_name"]!=""):
                degree.university=request.POST["university_name"]
            else:
                context["message"] = "فیلد نام دانشگاه باید مقدار دهی شود"
                context["status"]=False
                return  JsonResponse(context)
                
            if ("field_name" in request.POST and request.POST["field_name"]!=""):
                degree.field=request.POST["field_name"]
            else:
                context["message"] = "فیلد رشته تحصیلی باید مقدار دهی شود"
                context["status"]=False
            
            if ("orientation_name" in request.POST and request.POST["orientation_name"]!=""):
                degree.orientation=request.POST["orientation_name"]

            if ("degree_from_date" in request.POST and request.POST["degree_from_date"]!=""):
                degree.from_date=ConvertToMiladi(request.POST["degree_from_date"])

            if ("degree_to_date" in request.POST and request.POST["degree_to_date"]!=""):
                degree.to_date=ConvertToMiladi(request.POST["degree_to_date"])

            if ("degree_description" in request.POST and request.POST["degree_description"]!=""):
                degree.description=request.POST["degree_description"]
            
            degree.save()
            context["message"] = "مقطع تحصیلی با موفقیت ذخیره شد"
            context["status"]=True
    except Exception as ex:
        context["message"] = "بروز خطا"
        context["status"]=False
    return  JsonResponse(context)


@login_required(login_url='user:login') 
def ToList(request,user_id):
    data={}
    _user=User.objects.get(pk=user_id)
    if request.user.id not in _user.employee.GetEmployeeParentSet and request.user!=_user:
        raise PermissionDenied
    if _user.employee.GetEmployeeParent==request.user.id:
        data["direct_manager"]=True
    else:
        data["direct_manager"]=False
    degrees = DegreeSerializer(Degree.objects.filter(user__pk=user_id), many=True)
    data["degrees"]=JSONRenderer().render(degrees.data).decode("utf-8") 
    return JsonResponse(data)

@login_required(login_url='user:login') 
def Delete(request,degree_id):
    data={}
    try:
        degree=Degree.objects.get(pk=degree_id)
        _user=User.objects.get(pk=degree.user.id)
        if (_user.employee.GetEmployeeParent!=request.user.id):
            data["message"] = "شما مجوز حذف مدرک تحصیلی را ندارید."
            data["status"]=False
            return  JsonResponse(data)
        degree.delete()
        data["status"]=True
        data["message"]="حذف با موفقیت انجام شد"
        
    except Exception as err:
        data['message']=err.args[0]
        data["status"]=False
    return JsonResponse(data)


@login_required(login_url='user:login') 
def Detail(request,degree_id):
    data={}
    _user=Degree.objects.get(pk=degree_id).user
    if request.user.id not in _user.employee.GetEmployeeParentSet and request.user!=_user:
        raise PermissionDenied

    degrees = DegreeSerializer(Degree.objects.filter(pk=degree_id), many=True)
    data["degrees"]=JSONRenderer().render(degrees.data).decode("utf-8") 
    return JsonResponse(data)

@login_required(login_url='user:login') 
def Edit(request,degree_id):
    context={}
    try:
        if request.method == "POST":
            degree=Degree.objects.get(pk=degree_id)
            _user=User.objects.get(pk=degree.user.id)
            if (_user.employee.GetEmployeeParent!=request.user.id):
                context["message"] = "شما مجوز ویرایش مدرک تحصیلی را ندارید."
                context["status"]=False
                return  JsonResponse(context)
            degree=Degree.objects.get(pk=degree_id)
            if ("degree_level" in request.POST and int(request.POST["degree_level"])>0):
                degree.level=int(request.POST["degree_level"])
            else:
                context["message"] = "فیلد مقطع تحصیلی باید مقدار دهی شود"
                context["status"]=False
                return  JsonResponse(context)
            if ("university_name" in request.POST and request.POST["university_name"]!=""):
                degree.university=request.POST["university_name"]
            else:
                context["message"] = "فیلد نام دانشگاه باید مقدار دهی شود"
                context["status"]=False
                return  JsonResponse(context)
                
            if ("field_name" in request.POST and request.POST["field_name"]!=""):
                degree.field=request.POST["field_name"]
            else:
                context["message"] = "فیلد رشته تحصیلی باید مقدار دهی شود"
                context["status"]=False
            
            if ("orientation_name" in request.POST and request.POST["orientation_name"]!=""):
                degree.orientation=request.POST["orientation_name"]
            else:
                degree.orientation=""

            if ("degree_from_date" in request.POST and request.POST["degree_from_date"]!=""):
                degree.from_date=ConvertToMiladi(request.POST["degree_from_date"])
            else:
                degree.from_date=None

            if ("degree_to_date" in request.POST and request.POST["degree_to_date"]!=""):
                degree.to_date=ConvertToMiladi(request.POST["degree_to_date"])
            else:
                degree.to_date=None

            if ("degree_description" in request.POST and request.POST["degree_description"]!=""):
                degree.description=request.POST["degree_description"]
            else:
                degree.description=""
            
            degree.save()
            context["message"] = "مقطع تحصیلی با موفقیت ذخیره شد"
            context["status"]=True
    except Exception as ex:
        context["message"] =ex.args[0]# "بروز خطا"
        context["status"]=False
    return  JsonResponse(context)
