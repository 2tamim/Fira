from django.db.models import Q
from django.shortcuts import render, redirect
from django.http import HttpResponse, Http404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from ...models import ConsumingResource,Resource,ResourceTypeRelation,ResourceRelation,ResourceAssignment,ResourceType,ResourceTypeProperty,ResourcePropertyNum,ResourcePropertyText,Organization_Group,ResourceAssignment,ConsumingResource,Employee
import datetime,decimal
from django.http import JsonResponse
from django.core import serializers
from rest_framework.renderers import JSONRenderer
from django.core.exceptions import PermissionDenied
from ...utilities.date_tools import ConvertToMiladi, ConvertToSolarDate
from ...Serializers.resource_serializer import OrganizationGroupSerializer



def treelistchild(resource,all_resources):
    
    resource_pk=str(resource.pk)

    _consuming_resource=resource.consuming_resources.first()
    
    code=' کد : '+ resource_pk
    ip=""
    group=''
    tell=""
    account=''
    try:
        ip= resource.resource_type_property_text.filter(resource_type_property__slug='ip-vps-property').values('value').first()["value"].replace("<","&lt;").replace(">","&gt;")
    except:
        pass

    
    
    destinaton_resources=ResourceRelation.objects.filter(destinaton_resource=resource,deleted=None).values('source_resource__pk')
    resources = all_resources.filter(pk__in=destinaton_resources)

    status_color="infrastructure_node_status"   #default
    if _consuming_resource and  _consuming_resource.expiration:
        if _consuming_resource.expiration<datetime.date.today():
            status_color="infrastructure_node_expired_status"   #expired
        elif _consuming_resource.expiration<datetime.date.today()+datetime.timedelta(days=4) and _consuming_resource.expiration>datetime.date.today():
            status_color="infrastructure_node_expire_soon_status"   #expire soon

    
    
    if(len(resources) > 0):
        s = "<li class='nodes'><div  class='infrastructure_node'><div class='float_right  "+status_color+"'></div><div pk="+resource_pk+" id='resource_node_"+resource_pk+"' ip='"+ip+"' class='infrastructure_node_border cursor_pointer'"
        s+=" onclick='show_resource_detail("+resource_pk+")' ondblclick='changevisible("+resource_pk+")'>"
    
        s+="<img  class='rotated-arrow-icon arrow-icon' onclick='changevisible("+resource_pk+")' id='arrow_"+resource_pk+"' src=""\\static\\img\\icon\\arrow.svg"" >"
        s+="<div class='width_90percent'><div id='node_status_"+resource_pk+"' class=''/>"+str(resource.name).replace("<","&lt;").replace(">","&gt;")+ "</div><div class='width_100percent'><div class='width_50percent float_right'>"+code+"</div><div class='width_50percent float_right'>" + (ConvertToSolarDate(_consuming_resource.expiration) if _consuming_resource.expiration else "-")+"</div>"
    else:
        s = "<li class='nodes'><div class='display_flex infrastructure_node'><div class='"+status_color+"'></div><div  "
        s+=" id='resource_node_"+resource_pk+"' pk="+resource_pk+" ip='"+ip+"' class='infrastructure_node_border cursor_pointer' onclick='show_resource_detail("+resource_pk+")'><div class='width_90percent margin_right_10percent'><div id='node_status_"+resource_pk+"' class=''/>"+str(resource.name).replace("<","&lt;").replace(">","&gt;")+ "</div><div class='width_100percent'><div class='width_50percent float_right'>"+code+"</div><div class='width_50percent float_right'>" +   (ConvertToSolarDate(_consuming_resource.expiration) if _consuming_resource and _consuming_resource.expiration else "-")+"</div></div>"

    s += "</div></div>"
    # + "<br>"+code+"<div class='float_left'>" + 
    if len(resources) > 0:
        s += "<ul class='deactive nodes_"+resource_pk+"' >"
        for ch in resources:
            # _children = Task.objects.filter(task_parent_id=ch.id)
            s += treelistchild(ch,all_resources)
        s += "</ul>"

    s += "</li>"
    return (s)

# redirect when user is not logged in.
@login_required(login_url='user:login')
def ToList(request):
    request.session["activated_menu"]="infrastructure"
    context = {}
    context["switch_expire_show_consuming"]=False
    context["switch_logical_delete_show_consuming"]=False
    _tree = ""

    if len(request.user.locumtenens_organization_groups.all())>0 and request.user.locumtenens_organization_groups.first().locumtenens_active:
        as_user = request.user.locumtenens_organization_groups.first().manager
    else:
        as_user = request.user
    
    all_ch_uid = as_user.employee.GetAllChildrenUserId
    
    if request.method == "POST" and "switch_expire_show_consuming" in  request.POST:
        context["switch_expire_show_consuming"]=True
        _resource_id_list=[r["resource__pk"] for r in ConsumingResource.objects.filter(expiration__gte=datetime.date.today()).values('resource').values('resource__pk')]

        resources = Resource.objects.filter(resource_type__slug='vps-resource-type'  ).filter(Q(pk__in=ResourceAssignment.objects.filter(assignee=as_user).values('resource__pk')) |Q(pk__in=ResourceAssignment.objects.filter(assignee__id__in=all_ch_uid).values('resource__pk')) |Q(owner=as_user) | Q(owner__id__in=all_ch_uid )|Q(locumtenens=as_user) | Q(locumtenens__id__in=all_ch_uid )).exclude(Q(deleted=True)|Q(pk__in=_resource_id_list)).order_by('pk').prefetch_related('consuming_resources')
        all_resources = Resource.objects.filter(Q(pk__in=ResourceAssignment.objects.filter(assignee=as_user).values('resource__pk')) |Q(pk__in=ResourceAssignment.objects.filter(assignee__id__in=all_ch_uid).values('resource__pk')) |Q(owner=as_user) | Q(owner__id__in=all_ch_uid )|Q(locumtenens=as_user) | Q(locumtenens__id__in=all_ch_uid )).exclude(Q(deleted=True)|Q(pk__in=_resource_id_list)).order_by('pk').prefetch_related('consuming_resources')

    elif request.method == "POST" and "switch_logical_delete_show_consuming" in  request.POST:
        context["switch_logical_delete_show_consuming"]=True
        context["switch_expire_show_consuming"]=False
        resources = Resource.objects.filter(deleted=True,resource_type__slug='vps-resource-type' ).filter(Q(pk__in=ResourceAssignment.objects.filter(assignee=as_user).values('resource__pk')) |Q(pk__in=ResourceAssignment.objects.filter(assignee__id__in=all_ch_uid).values('resource__pk')) |Q(owner=as_user) | Q(owner__id__in=all_ch_uid )|Q(locumtenens=as_user) | Q(locumtenens__id__in=all_ch_uid )).order_by('pk').prefetch_related('consuming_resources')
        all_resources = Resource.objects.filter(deleted=True).filter(Q(pk__in=ResourceAssignment.objects.filter(assignee=as_user).values('resource__pk')) |Q(pk__in=ResourceAssignment.objects.filter(assignee__id__in=all_ch_uid).values('resource__pk')) |Q(owner=as_user) | Q(owner__id__in=all_ch_uid )|Q(locumtenens=as_user) | Q(locumtenens__id__in=all_ch_uid )).order_by('pk').prefetch_related('consuming_resources')
    else:
        context["switch_expire_show_consuming"]=False 
        _resource_id_list=[r["resource__pk"] for r in ConsumingResource.objects.filter(expiration__gte=datetime.date.today()).values('resource').values('resource__pk')]

        resources = Resource.objects.filter(resource_type__slug='vps-resource-type',pk__in=_resource_id_list ).filter(Q(pk__in=ResourceAssignment.objects.filter(assignee=as_user).values('resource__pk')) |Q(pk__in=ResourceAssignment.objects.filter(assignee__id__in=all_ch_uid).values('resource__pk')) |Q(owner=as_user) | Q(owner__id__in=all_ch_uid )|Q(locumtenens=as_user) | Q(locumtenens__id__in=all_ch_uid )).exclude(deleted=True).order_by('pk').prefetch_related('consuming_resources')
        all_resources = Resource.objects.filter(pk__in=_resource_id_list).filter(Q(pk__in=ResourceAssignment.objects.filter(assignee=as_user).values('resource__pk')) |Q(pk__in=ResourceAssignment.objects.filter(assignee__id__in=all_ch_uid).values('resource__pk')) |Q(owner=as_user) | Q(owner__id__in=all_ch_uid )|Q(locumtenens=as_user) | Q(locumtenens__id__in=all_ch_uid )).exclude(deleted=True).order_by('pk').prefetch_related('consuming_resources')
          


    not_root_resource_pk =  ResourceRelation.objects.filter(deleted=None,source_resource__in=resources,destinaton_resource__in=resources).values('source_resource__pk')

    roots = resources.exclude(pk__in=not_root_resource_pk).prefetch_related('consuming_resources')
    

    for r in roots:
        _tree += "<ul class='tree'>"
        _tree += treelistchild(r,all_resources)
        _tree += " </ul>"

    # for r in resources:
    #     _resource_relation=ResourceRelation.objects.filter(deleted=None,source_resource=r)

    #     if _resource_relation.count()==0 or (r.pk not in children_set and _resource_relation.first().destinaton_resource not in resources):
    #         i += 1
    #         _tree += "<ul class='tree'>"
    #         _tree += treelistchild(r.pk,all_resources)
    #         _tree += " </ul>"
    #         children_set.add(r.pk)

    context["tree"] = _tree
    return render(request, 'resource/infrastructure.html', {'context': context})