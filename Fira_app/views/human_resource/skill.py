from django.shortcuts import render, redirect
from django.http import HttpResponse, Http404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from ...models import Skill
import datetime
from ...utilities.date_tools import ConvertToMiladi, ConvertToSolarDate,DateTimeDifference,ConvertTimeDeltaToStringTime
from django.http import JsonResponse
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.core import serializers
from ...Serializers.human_resource_serializer import DegreeSerializer
from rest_framework.renderers import JSONRenderer

@login_required(login_url='user:login') #redirect when user is not logged in
def Add(request,user_id):
    context={}
    try:
        if request.method == "POST":
            _user=User.objects.get(pk=user_id)
            if (_user.employee.GetEmployeeParent!=request.user.id):
                context["message"] = "شما مجوز افزودن مهارت را ندارید."
                context["status"]=False
                return  JsonResponse(context)
            skill=Skill()
            skill.user=User.objects.get(pk=user_id)
            if ("skill_name" in request.POST and request.POST["skill_name"]!=""):
                skill.name=request.POST["skill_name"]
            else:
                context["message"] = "فیلد عنوان مهارت باید مقدار دهی شود"
                context["status"]=False
                return  JsonResponse(context)
            
            if ("SkillLevelInputId" in request.POST and int(request.POST["SkillLevelInputId"])>0):
                skill.level=request.POST["SkillLevelInputId"]

            if ("skill_description" in request.POST and request.POST["skill_description"]!=""):
                skill.description=request.POST["skill_description"]
            
            skill.save()
            context["message"] = "مهارت با موفقیت ذخیره شد"
            context["status"]=True
    except Exception as ex:
        context["message"] =ex.args[0]# "بروز خطا"
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
    data["skills"] = serializers.serialize('json',Skill.objects.filter(user__pk=user_id))
    
    return JsonResponse(data)

@login_required(login_url='user:login') 
def Delete(request,skill_id):
    data={}
    try:
        skill=Skill.objects.get(pk=skill_id)
        _user=User.objects.get(pk=skill.user.id)
        if (_user.employee.GetEmployeeParent!=request.user.id):
            data["message"] = "شما مجوز حذف مهارت را ندارید."
            data["status"]=False
            return  JsonResponse(data)
        skill.delete()
        data["status"]=True
        data["message"]="حذف با موفقیت انجام شد"
        
    except Exception as err:
        data["status"]=False
        data['message']=err.args[0]
    return JsonResponse(data)


@login_required(login_url='user:login') 
def Detail(request,skill_id):
    _user=Skill.objects.get(pk=skill_id).user
    if request.user.id not in _user.employee.GetEmployeeParentSet and request.user!=_user:
        raise PermissionDenied
    data={}
    data["skill"] = serializers.serialize('json',Skill.objects.filter(pk=skill_id))  
    return JsonResponse(data)

@login_required(login_url='user:login') 
def Edit(request,skill_id):
    context={}
    try:
        if request.method == "POST":
            skill=Skill.objects.get(pk=skill_id)
            _user=User.objects.get(pk=skill.user.id)
            if (_user.employee.GetEmployeeParent!=request.user.id):
                context["message"] = "شما مجوز ویرایش مهارت را ندارید."
                context["status"]=False
                return  JsonResponse(context)
            if ("skill_name" in request.POST and request.POST["skill_name"]!=""):
                skill.name=request.POST["skill_name"]
            else:
                context["message"] = "فیلد عنوان مهارت باید مقدار دهی شود"
                context["status"]=False
                return  JsonResponse(context)
            
            if ("SkillLevelInputId" in request.POST and int(request.POST["SkillLevelInputId"])>0):
                skill.level=request.POST["SkillLevelInputId"]
            else:
                skill.level=0
            if ("skill_description" in request.POST and request.POST["skill_description"]!=""):
                skill.description=request.POST["skill_description"]
            else:
                skill.description=''
            
            skill.save()
            context["message"] = "مهارت با موفقیت ذخیره شد"
            context["status"]=True
    except Exception as ex:
        context["message"] = "بروز خطا"
        context["status"]=False
    return  JsonResponse(context)
