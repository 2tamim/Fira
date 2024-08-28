from django.db.models import Q
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from ...models import Resource,ResourceAssignment,HardwareResource
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from ...Serializers.resource_serializer import HardwareResourceSerializer
from ...Serializers.task_management_serializer import UserSerializer
from rest_framework.renderers import JSONRenderer

# redirect when user is not logged in.
@login_required(login_url='user:login')
def index(request):
    if len(request.user.locumtenens_organization_groups.all())>0 and request.user.locumtenens_organization_groups.first().locumtenens_active:
        as_user = request.user.locumtenens_organization_groups.first().manager
    else:
        as_user = request.user
    
    all_ch_uid = as_user.employee.GetAllChildrenUserId

    request.session["activated_menu"]="resource_report"
    context = {}
    users=[]
    _resources=Resource.objects.filter(Q(owner=as_user)|Q(locumtenens=as_user)|Q(owner__id__in=all_ch_uid)|Q(locumtenens__id__in=all_ch_uid))
    users=[(r["assignee"]) for r in ResourceAssignment.objects.filter(resource__resource_type__category=2,resource__in=_resources,deleted=None).values('assignee')]
    users.append(as_user.pk)
    for u in all_ch_uid:
        users.append(u)
    
    context["users"]=User.objects.filter(pk__in=users)
    return render(request, 'resource/report.html', {'context': context})


# Report Search
@login_required(login_url='user:login') #redirect when user is not logged in
def GetHardwareResource(request):
    if len(request.user.locumtenens_organization_groups.all())>0 and request.user.locumtenens_organization_groups.first().locumtenens_active:
        as_user = request.user.locumtenens_organization_groups.first().manager
    else:
        as_user = request.user
    
    all_ch_uid = as_user.employee.GetAllChildrenUserId

    context={}
    if request.method == "POST":
        context["personel"]={}
        try:
            personel_keys =request.POST["resource_report_personel_key"].split(",")
            if (len(personel_keys)>0) and request.POST["resource_report_personel_key"].strip()!='':
                for p in personel_keys:
                    context["personel"][p]={}                    
                    _resources_in_assignment=[int(r["resource__pk"]) for r in ResourceAssignment.objects.filter(assignee__pk=p,deleted=None).filter(Q(resource__owner=as_user)\
                        |Q(resource__locumtenens=as_user)|Q(resource__owner__id__in=all_ch_uid)|Q(resource__locumtenens__id__in=all_ch_uid\
                            |Q(assignee=as_user)|Q(assignee__pk__in=all_ch_uid))).values('resource__pk')]
                    
                    user=User.objects.get(pk=p)
                    context["personel"][p]["name"]=user.first_name+" "+user.last_name
                    context["personel"][p]["personelnumber"]=(user.employee.personelnumber if user.employee.personelnumber else " - ")

                    _hardware_resource=HardwareResourceSerializer(HardwareResource.objects.filter(resource__in=Resource.objects.filter(pk__in=_resources_in_assignment)), many=True)
                    context["personel"][p]["resources"]=JSONRenderer().render(_hardware_resource.data).decode("utf-8")
                    context["message"] ="True"
            else:
                context["message"] = 'هیچ پرسنلی انتخاب نشده است'
        except Exception as ex:
            context["message"] ='متاسفانه خطایی رخ داده است'

    return  JsonResponse(context)
