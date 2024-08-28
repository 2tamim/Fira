from django.shortcuts import render, redirect
from django.http import HttpResponse, Http404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from ...models import Certificate
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
                context["message"] = "شما مجوز افزودن مدرک را ندارید."
                context["status"]=False
                return  JsonResponse(context)
            certificate=Certificate()
            certificate.user=User.objects.get(pk=user_id)
            if ("certificate_name" in request.POST and request.POST["certificate_name"]!=""):
                certificate.name=request.POST["certificate_name"]
            else:
                context["message"] = "فیلد عنوان مدرک باید مقدار دهی شود"
                context["status"]=False
                return  JsonResponse(context)
            
            if ("CertificateMarkInputId" in request.POST and int(request.POST["CertificateMarkInputId"])>0):
                certificate.mark=request.POST["CertificateMarkInputId"]

            if ("certificate_organization_name" in request.POST and request.POST["certificate_organization_name"]!=""):
                certificate.organization=request.POST["certificate_organization_name"]

            if ("certificate_description" in request.POST and request.POST["certificate_description"]!=""):
                certificate.description=request.POST["certificate_description"]
            
            certificate.save()
            context["message"] = "مدرک با موفقیت ذخیره شد"
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
    data["certificates"] = serializers.serialize('json',Certificate.objects.filter(user__pk=user_id))
    
    return JsonResponse(data)

@login_required(login_url='user:login') 
def Delete(request,certificate_id):
    data={}
    try:
        certificate=Certificate.objects.get(pk=certificate_id)
        _user=User.objects.get(pk=certificate.user.id)
        if (_user.employee.GetEmployeeParent!=request.user.id):
            data["message"] = "شما مجوز حذف مدرک را ندارید."
            data["status"]=False
            return  JsonResponse(data)
        certificate.delete()
        data["message"]="حذف با موفقیت انجام شد"
        data["status"]=True
    except Exception as err:
        data['message']=err.args[0]
        data["status"]=False
    return JsonResponse(data)


@login_required(login_url='user:login') 
def Detail(request,certificate_id):
    _user=Certificate.objects.get(pk=certificate_id).user
    if request.user.id not in _user.employee.GetEmployeeParentSet and request.user!=_user:
        raise PermissionDenied
    data={}
    data["certificate"] = serializers.serialize('json',Certificate.objects.filter(pk=certificate_id))  
    return JsonResponse(data)

@login_required(login_url='user:login') 
def Edit(request,certificate_id):
    context={}
    try:
        if request.method == "POST":
            certificate=Certificate.objects.get(pk=certificate_id)
            _user=User.objects.get(pk=certificate.user.id)
            if (_user.employee.GetEmployeeParent!=request.user.id):
                context["message"] = "شما مجوز ویرایش مدرک را ندارید."
                context["status"]=False
                return  JsonResponse(context)
            if ("certificate_name" in request.POST and request.POST["certificate_name"]!=""):
                certificate.name=request.POST["certificate_name"]
            else:
                context["message"] = "فیلد عنوان مدرک باید مقدار دهی شود"
                context["status"]=False
                return  JsonResponse(context)
            
            if ("CertificateMarkInputId" in request.POST and int(request.POST["CertificateMarkInputId"])>0):
                certificate.mark=request.POST["CertificateMarkInputId"]
            else:
                certificate.mark=0

            if ("certificate_organization_name" in request.POST and request.POST["certificate_organization_name"]!=""):
                certificate.organization=request.POST["certificate_organization_name"]
            else:
                certificate.organization=''

            if ("certificate_description" in request.POST and request.POST["certificate_description"]!=""):
                certificate.description=request.POST["certificate_description"]
            else:
                certificate.description=''
            
            certificate.save()
            context["message"] = "مدرک با موفقیت ذخیره شد"
            context["status"]=True
    except Exception as ex:
        context["message"] =ex.args[0]# "بروز خطا"
        context["status"]=False
    return  JsonResponse(context)
