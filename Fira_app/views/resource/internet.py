from django.db.models import Q
from django.shortcuts import render, redirect
from django.http import HttpResponse, Http404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from ...models import Resource,ResourceAssignment,ResourceType,ResourceTypeProperty,ResourcePropertyNum,ResourcePropertyText,Organization_Group,ResourceAssignment,ConsumingResource,Employee
import datetime,decimal
from django.http import JsonResponse
from django.core import serializers
from django.db.models import Subquery,OuterRef
from rest_framework.renderers import JSONRenderer
from django.core.exceptions import PermissionDenied
from ...utilities.date_tools import ConvertToMiladi, ConvertToSolarDate,GetPersianMonthName
from ...Serializers.resource_serializer import OrganizationGroupSerializer
# redirect when user is not logged in
@login_required(login_url='user:login')
def ToList(request):
    request.session["activated_menu"]="internet"
    context = {}

    
    _date_time_now=datetime.datetime.now()
    context["this_year"]=int(ConvertToSolarDate(_date_time_now).split("/")[0])
    context["list_this_year_range"]=range(1390,int(ConvertToSolarDate(_date_time_now).split("/")[0])+1)
    context["this_month"]=int(ConvertToSolarDate(_date_time_now).split("/")[1])-1
    if (context["this_month"]<1):
        context["this_month"]=12
        context["this_year"]=context["this_year"]-1

    return render(request, 'resource/internet.html', {'context': context})

# redirect when user is not logged in
@login_required(login_url='user:login')
def GetInternetData(request,year,month,order_id):
    if len(request.user.locumtenens_organization_groups.all())>0 and request.user.locumtenens_organization_groups.first().locumtenens_active:
        as_user = request.user.locumtenens_organization_groups.first().manager
    else:
        as_user = request.user
    
    all_ch_uid = as_user.employee.GetAllChildrenUserId

    context = {}
    
    context["max_number"]=0
    _miladi_start_date=ConvertToMiladi(str(year)+"/"+str(month)+"/01")
    _miladi_end_date=ConvertToMiladi(str(year)+"/"+str(month)+"/31")
    
    _consuming_resource=ConsumingResource.objects.filter(expiration__gte=_miladi_start_date,expiration__lte=_miladi_end_date).values('resource__pk')
    resources=Resource.objects.filter(Q(owner=as_user)|Q(locumtenens=as_user)|Q(owner__pk__in=all_ch_uid)|Q(locumtenens__pk__in=all_ch_uid)\
        |Q(pk__in=ResourceAssignment.objects.filter(Q(assignee__pk__in=all_ch_uid)|Q(assignee=as_user)).values('resource__pk')) ).filter(resource_type__slug='consuminginternet',pk__in=_consuming_resource)
    _valid_assignee=ResourceAssignment.objects.filter(resource__pk__in=resources.values('pk')).values('assignee__pk')

    _valid_organization_group=Employee.objects.filter(user__pk__in=_valid_assignee).values('organization_group__pk')
    organization_group=Organization_Group.objects.filter(pk__in=_valid_organization_group)

    # organization_group=OrganizationGroupSerializer(Organization_Group.objects.filter(pk__in=_valid_organization_group), many=True)

    # context["organization_groups"] = JSONRenderer().render(organization_group.data).decode("utf-8")
    context["resources"]=[]
    for r in resources:
        resource_data={}
        _resource_assignment=ResourceAssignment.objects.filter(resource=r).first()

        if _resource_assignment and _resource_assignment.assignee and _resource_assignment.assignee.employee:
            resource_data["pk"]=r.pk
            resource_data["assignee_id"]=_resource_assignment.assignee.id
            resource_data["assignee_user_name"]=_resource_assignment.assignee.get_full_name()
            resource_data["user_avatar"]=str(_resource_assignment.assignee.employee.avatar)
            resource_data["organization_id"]=_resource_assignment.assignee.employee.organization_group.id
            resource_data["organization_name"]=_resource_assignment.assignee.employee.organization_group.name
            resource_data["operation"]=r.consuming_resources.all().last().op_area.name + (("-" + r.consuming_resources.all().last().op_project.name) if r.consuming_resources.all().last().op_project else "")
            _upload=ResourcePropertyNum.objects.filter(resource=r,resource_type_property__slug='consuminginternetupload').first()
            _download=ResourcePropertyNum.objects.filter(resource=r,resource_type_property__slug='consuminginternetdownload').first()
            try:
                if _upload.value+_download.value>context["max_number"]:
                    context["max_number"]=_upload.value+_download.value
            
                resource_data["Upload"]=_upload.value
                resource_data["Download"]=_download.value
            except:
                pass
            resource_data["order"]=0
            context["resources"].append(resource_data)
    
    context["sorted_resources"]=[]
    for r1 in context["resources"]:
        counter=0
        for r2 in context["resources"]:
            try:
                if r1["Upload"]+r1["Download"]<r2["Upload"]+r2["Download"] and order_id==1:
                    counter+=1;
                elif r1["Upload"]+r1["Download"]>r2["Upload"]+r2["Download"] and order_id==2:
                    counter+=1;
                elif r1["Download"]<r2["Download"] and order_id==3:
                    counter+=1;
                elif r1["Download"]>r2["Download"] and order_id==4:
                    counter+=1;
                elif r1["Upload"]<r2["Upload"] and order_id==5:
                    counter+=1;
                elif r1["Upload"]>r2["Upload"] and order_id==6:
                    counter+=1;
                elif r1["assignee_user_name"]>r2["assignee_user_name"]and order_id==7:
                    counter+=1;
            except:
                pass
        r1["order"]=counter
        
    counter=0
    for r1 in context["resources"]:   
        for r2 in context["resources"]:    ##sort
            if r2["order"]==counter:
                context["sorted_resources"].append(r2)
        counter+=1

    context["organization_groups"]=[]
    context["organization_max_number"]=0
    for org in organization_group:
        org_data={}
        org_data["id"]=org.id
        org_data["name"]=org.name
        org_data["Upload"]=0
        org_data["Download"]=0
        org_data["order"]=0
        for r in context["sorted_resources"]:
            if r["organization_id"]==org.id:
                try:
                    org_data["Upload"]+=r["Upload"]
                except:
                    pass
                try:
                    org_data["Download"]+=r["Download"]
                except:
                    pass
        try:
            if(context["organization_max_number"]<org_data["Upload"]+org_data["Download"]):
                context["organization_max_number"]=org_data["Upload"]+org_data["Download"]
        except:
            pass
        context["organization_groups"].append(org_data)
    
    for org1 in context["organization_groups"]:
        counter=0
        for org2 in context["organization_groups"]:
            try:
                if org1["Upload"]+org1["Download"]<org2["Upload"]+org2["Download"] and order_id==1:
                    counter+=1;
                elif org1["Upload"]+org1["Download"]>org2["Upload"]+org2["Download"] and order_id==2:
                    counter+=1;
                elif org1["Download"]<org2["Download"] and order_id==3:
                    counter+=1;
                elif org1["Download"]>org2["Download"] and order_id==4:
                    counter+=1;
                elif org1["Upload"]<org2["Upload"] and order_id==5:
                    counter+=1;
                elif org1["Upload"]>org2["Upload"] and order_id==6:
                    counter+=1;
                elif org1["name"]>org2["name"]and order_id==7:
                    counter+=1;
            except:
                pass
        org1["order"]=counter

    
    counter=0
    context["sorted_organization_groups"]=[]
    for org1 in context["organization_groups"]:
        for org2 in context["organization_groups"]:    ##sort
            if org2["order"]==counter:
                context["sorted_organization_groups"].append(org2)
        counter+=1
    return JsonResponse(context)


# redirect when user is not logged in
@login_required(login_url='user:login')
def GetInternetUserDataInYear(request,user_id,year):
    context={}
    _miladi_start_date=ConvertToMiladi(str(year)+"/01/01")
    _miladi_end_date=ConvertToMiladi(str(year)+"/12/30")
    _requested_uesr=User.objects.get(pk=user_id)
    _consuming_resource=ConsumingResource.objects.filter(resource__resource_type__slug='consuminginternet',expiration__gte=_miladi_start_date,expiration__lte=_miladi_end_date)\
        .filter(Q(resource__owner=request.user)|Q(resource__locumtenens=request.user)|Q(resource__owner__pk__in=request.user.employee.GetAllChildrenUserId)|Q(resource__locumtenens__pk__in=request.user.employee.GetAllChildrenUserId)\
            |Q(resource__pk__in=ResourceAssignment.objects.filter(Q(assignee__pk=user_id)|Q(assignee__pk__in=_requested_uesr.employee.GetEmployeeParentSet),pk=Subquery(ResourceAssignment.objects.filter(resource__id=OuterRef('resource__pk'),).order_by('-id').values('id')[:1])).values('resource__id')))\
                .filter(resource__pk__in=ResourceAssignment.objects.filter(assignee__pk=user_id,pk=Subquery(ResourceAssignment.objects.filter(resource__id=OuterRef('resource__pk'),).order_by('-id').values('id')[:1])).values('resource__id')).order_by('expiration')
    print(_consuming_resource)
    for r in _consuming_resource:
        _date=ConvertToSolarDate(r.expiration).split("/")
        _upload=ResourcePropertyNum.objects.filter(resource=r.resource,resource_type_property__slug='consuminginternetupload').first()
        _download=ResourcePropertyNum.objects.filter(resource=r.resource,resource_type_property__slug='consuminginternetdownload').first()
        context[GetPersianMonthName(_date[1])]=[_upload.value,_download.value]

    return JsonResponse(context)
    
    
    