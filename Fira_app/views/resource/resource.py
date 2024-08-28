from django.db import models
from django.db.models import Q,Value,F,Window,Prefetch,Subquery,OuterRef,Count
from django.db.models.functions.window import FirstValue
from django.db.models.functions import Concat,Cast
from django.shortcuts import render, redirect
from django.http import HttpResponse, Http404
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User
from ...models import Task,Resource,ResourceAssignment,ResourceType,ResourceTypeProperty,ResourcePropertyNum,ResourcePropertyText\
    ,ResourcePropertyDate,ResourcePropertyFile,ResourcePropertyBool,ResourceTypeRelation,ResourceRelation,HardwareResource\
        ,ConsumingResource,Notification,Organization_Group , ResourceTaskAssignment, OPArea, OPProject
import datetime,decimal
from django.db import transaction
from ...utilities.date_tools import ConvertToMiladi, ConvertToSolarDate,GetWeekDay,DateTimeDifference,ConvertTimeDeltaToStringTime
from django.http import JsonResponse
from django.core import serializers
from rest_framework.renderers import JSONRenderer
from ...Serializers.resource_serializer import ResourceRelationSerializer,ResourceAssignmentSerializer,ResourceSerializer,\
    HardwareResourceSerializer,ConsumingResourceSerializer,ResourcePropertyNumSerializer,ResourcePropertyTextSerializer,\
        ResourcePropertyBoolSerializer,ResourcePropertyFileSerializer,ResourcePropertyDateSerializer , ResourceTaskSerializer\
            ,ResourceMiniSerializer, ResourceTypeRelationMiniSerializer, ResourceRelationMiniSerializer
from django.core.exceptions import PermissionDenied
from openpyxl import Workbook
from django.contrib.postgres.search import SearchVector, SearchQuery,SearchRank

@login_required(login_url='user:login') #redirect when user is not logged in
@transaction.atomic
def add(request,**kwargs):
    if len(request.user.locumtenens_organization_groups.all())>0 and request.user.locumtenens_organization_groups.first().locumtenens_active:
        as_user = request.user.locumtenens_organization_groups.first().manager
    else:
        as_user = request.user

    resource_id=kwargs.get('resource_id',None)
    request.session["activated_menu"]="add_resource"
    context={}
    context["op_areas"] = OPArea.objects.all()
    context["op_projects"] = OPProject.objects.all()

    _resource_id=0
    if (resource_id):

        _resource_id=resource_id
        _resource=Resource.objects.get(pk=_resource_id)
        
        if not(_resource.owner == as_user or _resource.locumtenens == as_user or _resource.creator== as_user or as_user.id in _resource.creator.employee.GetEmployeeParentSet or as_user.id in _resource.owner.employee.GetEmployeeParentSet or as_user.id in _resource.locumtenens.employee.GetEmployeeParentSet ):
            raise PermissionDenied
        context["data"]={}
        context["data"]["resource_add_name"]=_resource.name
        context["data"]["resource_add_description"]=_resource.description
        if _resource.owner:
            context["data"]["resource_add_owner"]=_resource.owner.id
        if _resource.locumtenens:
            context["data"]["resource_add_locumtenens"]=_resource.locumtenens.id
        context["data"]["resource_add_assignee"]=[]
        context["data"]["resource_add_assignee_pk_list"]=""
        assignee_pk_list=""
        for assigner in ResourceAssignment.objects.filter(resource=_resource,deleted=None):
            context["data"]["resource_add_assignee"].append(assigner.assignee)
            assignee_pk_list+=str(assigner.assignee.id)+","
        assignee_pk_list=assignee_pk_list[:-1]
        context["data"]["resource_add_assignee_pk_list"]=assignee_pk_list
        

        context["data"]["resource_add_price"]=_resource.price
        context["data"]["resource_add_type"]=_resource.resource_type.id
        if _resource.task:
            context["data"]["resource_task_id"]=_resource.task.id
            context["resource_tasks"]=Task.objects.filter(Q(task_type__resource_type__pk=_resource.resource_type.id,progress__gte=0,progress__lt=100,user_assignee=request.user)|Q(pk=_resource.task.id))
        else:
            context["resource_tasks"]=Task.objects.filter(task_type__resource_type__pk=_resource.resource_type.id,progress__gte=0,progress__lt=100,user_assignee=request.user)
            
        if _resource.resource_type.category==1 :  # 1-consuming resource
            try:
                _consuming_resource=ConsumingResource.objects.filter(resource__id=_resource_id).order_by('-pk').first()
                if _consuming_resource:
                    if _consuming_resource.expiration:
                        context["data"]["consuming_resource_expiration"]=ConvertToSolarDate(_consuming_resource.expiration)
                    context["data"]["consuming_resource_total_amount"]=_consuming_resource.total_amount
                    context["data"]["consuming_resource_consumed_amount"]=_consuming_resource.consumed_amount
                    context["data"]["consuming_resource_price"]=_consuming_resource.price
                    # context["data"]["consuming_resource_project"]=_consuming_resource.project
                    context["data"]["consuming_resource_op_project"]=_consuming_resource.op_project
                    context["data"]["consuming_resource_op_area"]=_consuming_resource.op_area
            except:
                pass
        elif _resource.resource_type.category==2 :  # 1-hardware resource
            try:
                _hardware_resource=HardwareResource.objects.get(resource__id=_resource_id)
                if _hardware_resource:
                    context["data"]["hardware_resource_code"]=_hardware_resource.code
                    context["data"]["hardware_resource_serial"]=_hardware_resource.serial
                    context["data"]["hardware_resource_return_status"]=_hardware_resource.return_status
                    if _hardware_resource.return_date:
                        context["data"]["hardware_resource_return_date"]=ConvertToSolarDate(_hardware_resource.return_date)
                    context["data"]["hardware_resource_health"]=_hardware_resource.health
                    context["data"]["hardware_resource_repair"]=_hardware_resource.repair
                    context["data"]["hardware_resource_manufacturer"]=_hardware_resource.manufacturer

                    _hardware=HardwareResource.objects.filter(code=_hardware_resource.code).exclude(resource__pk=_resource_id)
                
                    if _hardware and len(_hardware)>0:
                        context["hardware_resource_code_replicated"]=True
                    else:
                        context["hardware_resource_code_replicated"]=False
            except:
                pass
    else:
        if request.method == "GET":
            context["data"]={}
            context["data"]["hardware_resource_health"]=True
    
    context["resource_id"]=_resource_id

    context["user"] = User.objects.all().exclude(username='admin').order_by('last_name')
    context["resource_type"] = ResourceType.objects.filter(pk__in=request.user.employee.CreatableResTypes)

    if request.method == "POST":
        context["data"]=request.POST
        try:
            with transaction.atomic():
                resource=None
                if (_resource_id):
                    resource=Resource.objects.get(pk=_resource_id)
                    
                else:
                    resource=Resource()
                    resource.creator=request.user

                if (not request.POST["resource_add_name"]):
                    context["Error"] = "فیلد عنوان منبع باید مقدار دهی شود"
                    return render(request, 'resource/add.html', {'context':context})
                else:
                    resource.name=request.POST["resource_add_name"]
                
                if (request.POST["resource_add_description"]):
                    resource.description=request.POST["resource_add_description"]
                else:
                    resource.description=""

                # if (int(request.POST["resource_add_owner"])):
                #     resource.owner=User.objects.get(pk=int(request.POST["resource_add_owner"]))
                # else:
                #     context["Error"] = "فیلد مالک باید مقدار دهی شود"
                #     return render(request, 'resource/add.html', {'context':context})
                if not resource.owner:
                    resource.owner = request.user
                
                if (int(request.POST["resource_add_locumtenens"])):
                    resource.locumtenens=User.objects.get(pk=int(request.POST["resource_add_locumtenens"]))
                else:
                    resource.locumtenens=None

                if (request.POST["resource_add_price"]):
                    resource.price=decimal.Decimal(request.POST["resource_add_price"].replace(",", ""))
                else:
                    resource.price=0

                if (int(request.POST["resource_add_type"])):
                    resource.resource_type=ResourceType.objects.get(pk=int(request.POST["resource_add_type"]))
                    if resource.resource_type not in ResourceType.objects.filter(pk__in=request.user.employee.CreatableResTypes):
                        context["Error"] = "شما مجاز به تعریف منبعی از این نوع نیستید"
                        return render(request, 'resource/add.html', {'context':context})
                else:
                    context["Error"] = "فیلد نوع منبع باید مقدار دهی شود"
                    return render(request, 'resource/add.html', {'context':context})
                
                if (int(request.POST["resource_task"])):
                    resource.task=Task.objects.get(pk=int(request.POST["resource_task"]))
                else:
                    resource.task=None

                if resource.resource_type.category==1:
                    if (not request.POST["consuming_resource_expiration"] and not request.POST["consuming_resource_total_amount"]):
                        context["Error"] = "یکی از فیلدهای تاریخ انقضاء و حجم کل باید مقدار دهی شود"
                        return render(request, 'resource/add.html', {'context':context})

                if (request.POST["consuming_resource_op_project"]) and int(request.POST["consuming_resource_op_project"]) > 0:
                    if OPProject.objects.get(id = int(request.POST["consuming_resource_op_project"])).area != OPArea.objects.get(id = int(request.POST["consuming_resource_op_area"])):
                        context["Error"] = "پروژه انتخاب شده مربوط به این محور عملیاتی نیست"
                        return render(request, 'resource/add.html', {'context':context})

                resource.save()
                
                consuming_resource=None
                hardware_resource=None
                if resource.resource_type.category==1:
                    if (_resource_id):
                        
                        consuming_resource=ConsumingResource.objects.filter(resource__id=_resource_id).order_by('-pk').first()
                        if( not consuming_resource):
                            consuming_resource=ConsumingResource()
                    else:
                        consuming_resource=ConsumingResource()
                    consuming_resource.resource=resource
                    if(request.POST["consuming_resource_price"]):
                        consuming_resource.price=decimal.Decimal(request.POST["consuming_resource_price"])
                    else:
                        consuming_resource.price=0

                    # if(request.POST["consuming_resource_project"]):
                    #     consuming_resource.project=request.POST["consuming_resource_project"]
                    # else:
                    #     consuming_resource.project=0

                    if(request.POST["consuming_resource_op_project"]) and int(request.POST["consuming_resource_op_project"]) > 0:
                        consuming_resource.op_project_id=request.POST["consuming_resource_op_project"]
                    else:
                        consuming_resource.op_project=None

                    if(request.POST["consuming_resource_op_area"]):
                        consuming_resource.op_area_id=request.POST["consuming_resource_op_area"]
                    else:
                        consuming_resource.op_area=None

                    if(request.POST["consuming_resource_total_amount"]):
                        consuming_resource.total_amount=decimal.Decimal(request.POST["consuming_resource_total_amount"])
                    else:
                        consuming_resource.total_amount=0

                    if(request.POST["consuming_resource_consumed_amount"]):
                        consuming_resource.consumed_amount=decimal.Decimal(request.POST["consuming_resource_consumed_amount"])
                    else:
                        consuming_resource.consumed_amount=0

                    if(request.POST["consuming_resource_expiration"] and request.POST["consuming_resource_expiration"]!=""):
                        consuming_resource.expiration=ConvertToMiladi(request.POST["consuming_resource_expiration"])
                        #----------------Notification for expire
                        notification=Notification()
                        if resource.expire_notification:
                            notification=Notification.objects.get(pk=resource.expire_notification.pk)
                        notification.title="انقضاء منبع"
                        notification.user=resource.owner
                        notification.displaytime =  datetime.datetime.strptime(consuming_resource.expiration,'%Y-%m-%d') - datetime.timedelta(days=4)
                        notification.messages="منبع "+ resource.name +" در تاریخ "+ ConvertToSolarDate(consuming_resource.expiration) +" منقضی می شود"
                        notification.link="/resource/"+str(resource.pk)+"/list/"
                        notification.closed=False
                        notification.save()
                        #----------------Notification
                        resource.expire_notification=notification
                        resource.save()

                    else:
                        consuming_resource.expiration=None

                    
                elif resource.resource_type.category==2:
                    if (_resource_id):
                        
                        hardware_resource=HardwareResource.objects.get(resource__id=_resource_id)
                        if(not hardware_resource):
                            hardware_resource=HardwareResource()
                    else:
                        hardware_resource=HardwareResource()
                    hardware_resource.resource=resource
                    if (request.POST["hardware_resource_code"]):
                        hardware_resource.code=request.POST["hardware_resource_code"]
                    else:
                        hardware_resource.code=""
                    if (request.POST["hardware_resource_serial"]):
                        hardware_resource.serial=request.POST["hardware_resource_serial"]
                    else:
                        hardware_resource.serial=""
                    if("hardware_resource_return_status" in request.POST and request.POST["hardware_resource_return_status"]):
                        hardware_resource.return_status=True
                        hardware_resource.resource.assignements.all().update(deleted=datetime.datetime.now())
                    else:
                        hardware_resource.return_status=False

                    if(request.POST["hardware_resource_return_date"]):
                        hardware_resource.return_date=ConvertToMiladi(request.POST["hardware_resource_return_date"])
                    else:
                        hardware_resource.return_date=None

                    if( "hardware_resource_health" in request.POST and request.POST["hardware_resource_health"]):
                        hardware_resource.health=True
                    else:
                        hardware_resource.health=False

                    if("hardware_resource_repair" in request.POST and request.POST["hardware_resource_repair"]):
                        hardware_resource.repair=True
                    else:
                        hardware_resource.repair=False

                    if(request.POST["hardware_resource_manufacturer"]):
                        hardware_resource.manufacturer=request.POST["hardware_resource_manufacturer"]
                    else:
                        hardware_resource.manufacturer=""
                else:
                    pass
                
                if resource.expire_notification and resource.resource_type.category==2:
                    notification=Notification.objects.get(pk=resource.expire_notification.pk)
                    notification.delete()
                    #----------------Notification
                    resource.expire_notification=None
                    resource.save()

                _old_assigners=[]
                for assigner in ResourceAssignment.objects.filter(resource=resource,deleted=None):
                    _old_assigners.append(assigner.assignee.pk)
                
                #------------------------------- assigners
                _resource_assigners=request.POST["resource_Assignee_id_list"].split(",")
                for assigner in _resource_assigners:
                    if assigner  and assigner !='0' and int(assigner) not in _old_assigners:
                        _resource_assigner=ResourceAssignment()
                        _resource_assigner.assignee=User.objects.get(pk=assigner)
                        _resource_assigner.resource =resource
                        _resource_assigner.save()
                        #----------------Notification for assign
                        notification=Notification()
                        notification.title="منبع جدید"
                        notification.user=User.objects.get(pk=assigner)
                        notification.displaytime=datetime.datetime.now()
                        notification.messages="منبع "+ resource.name +" در تاریخ "+ ConvertToSolarDate(datetime.datetime.now()) +" به شما تخصیص داده شده است "
                        notification.link="/resource/"+str(resource.pk)+"/list/"
                        notification.closed=False
                        notification.save()
                        #----------------Notification
                        _resource_assigner.assignee_notification=notification
                        _resource_assigner.save()
                           

                for old_assignee in _old_assigners:
                    if str(old_assignee) not in _resource_assigners:
                        _resource_assigner=ResourceAssignment.objects.get(resource__id=_resource_id,assignee__id=old_assignee,deleted=None)
                        _resource_assigner.deleted =datetime.datetime.now()
                        _resource_assigner.save()

                        notification=Notification.objects.get(pk=_resource_assigner.assignee_notification.pk)
                        notification.closed=True
                        notification.save()
                
                #-------------------------------
                if resource.resource_type.category==1:
                    consuming_resource.save()
                elif resource.resource_type.category==2:
                    hardware_resource.save()
                _all_property_of_resource_type=ResourceTypeProperty.objects.filter(resource_type=resource.resource_type)
                
                if (len(_all_property_of_resource_type)>0):
                    for p in _all_property_of_resource_type:
                        _property_name="property_"+str(p.id)
                        try:
                            if p.value_type==1 and _property_name in request.POST:    # 1 = Property_Num
                                _resource_property_num=None
                                
                                try:
                                    _resource_property_num=ResourcePropertyNum.objects.get(resource_type_property=p,resource=resource)
                                except:
                                    _resource_property_num=ResourcePropertyNum()
                                
                                
                                _resource_property_num.resource=resource
                                _resource_property_num.resource_type_property=p
                                _resource_property_num.value=decimal.Decimal(request.POST[_property_name])
                                _resource_property_num.save()
                            elif p.value_type==2 and _property_name in request.POST:    # 2 = Property_Text
                                _resource_property_text=None
                                try:
                                    _resource_property_text=ResourcePropertyText.objects.get(resource_type_property=p,resource=resource)
                                except:
                                    _resource_property_text=ResourcePropertyText()
                                _resource_property_text.resource=resource
                                _resource_property_text.resource_type_property=p
                                _resource_property_text.value=request.POST[_property_name]
                                _resource_property_text.save()
                            elif p.value_type==3 and _property_name in request.POST:    # 3 = Property_date
                                _resource_property_date=None
                                try:
                                    _resource_property_date=ResourcePropertyDate.objects.get(resource_type_property=p,resource=resource)
                                except:
                                    _resource_property_date=ResourcePropertyDate()
                                _resource_property_date.resource=resource
                                _resource_property_date.resource_type_property=p
                                _resource_property_date.value=ConvertToMiladi(request.POST[_property_name])
                                _resource_property_date.save()
                            elif p.value_type==4 and _property_name in request.FILES:    # 4 = Property_File
                                _resource_property_file=None
                                try: 
                                    _resource_property_file=ResourcePropertyFile.objects.get(resource_type_property=p,resource=resource)
                                    _resource_property_file.value.delete()
                                except:
                                    _resource_property_file=ResourcePropertyFile()
                                _resource_property_file.resource=resource
                                _resource_property_file.resource_type_property=p
                                _resource_property_file.value=request.FILES[_property_name]
                                _resource_property_file.filename=request.FILES[_property_name].name
                                _resource_property_file.save()
                                
                                
                                
                            elif p.value_type==4 and _property_name not in request.FILES and _resource_id :    # 4 = Property_File
                                if _property_name in request.POST  and "status_"+_property_name in request.POST and request.POST["status_"+_property_name]=='delete':
                                    _resource_property_file=ResourcePropertyFile.objects.get(resource_type_property=p,resource=resource)
                                    _resource_property_file.value.delete()
                                    _resource_property_file.delete()

                            elif p.value_type==5 and _property_name in request.POST:    # 5 = Property_bool
                                try:
                                    _resource_property_bool=ResourcePropertyBool.objects.get(resource_type_property=p,resource=resource)
                                except:
                                    _resource_property_bool=ResourcePropertyBool()
                                _resource_property_bool.resource=resource
                                _resource_property_bool.resource_type_property=p
                                _resource_property_bool.value=True
                                _resource_property_bool.save()
                            elif p.value_type==5 and _property_name not in request.POST and _resource_id:    # 5 = Property_bool
                                
                                _resource_property_bool=ResourcePropertyBool.objects.get(resource_type_property=p,resource=resource)    
                                _resource_property_bool.value=False
                                _resource_property_bool.save()
                            
                            
                        except Exception as ex:
                            pass
                
                # if _resource_id:
                #     for r in ResourceRelation.objects.filter(source_resource=resource):
                #         r.delete()

                
                _resource_type_relation=ResourceTypeRelation.objects.filter(source_resource_type=resource.resource_type)
                if (len(_resource_type_relation)>0):
                    for r in _resource_type_relation:
                        _resource_type_relation_name="resource_type_relation_"+str(r.id)
                        if _resource_type_relation_name in request.POST:   
                            _resources=request.POST.getlist(_resource_type_relation_name)
                            _old_resource_relations=ResourceRelation.objects.filter(source_resource=resource,relation_type=r,deleted=None)
                            _old_resource_relations_destinaton=[]
                            
                            for el in _old_resource_relations:
                                _old_resource_relations_destinaton.append(el.destinaton_resource.id)
                                try:
                                    if  str(el.destinaton_resource.id) not in _resources:
                                        el.deleted=datetime.datetime.now()
                                        el.save()
                                except:
                                    pass
                            for res in _resources:
                                if res  and res !='0' and int(res) not in _old_resource_relations_destinaton:
                                    _resource_relation=ResourceRelation()
                                    _resource_relation.relation_type=r
                                    _resource_relation.source_resource = resource
                                    _resource_relation.destinaton_resource =Resource.objects.get(pk=res)
                                    _resource_relation.save()

                        else:
                            _old_resource_relations=ResourceRelation.objects.filter(source_resource=resource,relation_type=r,deleted=None)
                            for _old in _old_resource_relations:
                                _old.deleted=datetime.datetime.now()
                                _old.save()
                        
                context["Message"] = "ذخیره شد"
                try:
                    return redirect(request.GET['next'])
                except:
                    return redirect("resource:resource_list")
        except Exception as ex:
            context["Error"] = ex.args[0]
            
    return render(request, 'resource/add.html', {'context':context})

@login_required(login_url='user:login') #redirect when user is not logged in
@csrf_exempt
def ToList(request,**kwargs):
    if len(request.user.locumtenens_organization_groups.all())>0 and request.user.locumtenens_organization_groups.first().locumtenens_active:
        as_user = request.user.locumtenens_organization_groups.first().manager
    else:
        as_user = request.user

    request.session["activated_menu"]="resources_list"
    resource_id=kwargs.get('resource_id',None)

    # useful variables defined to increase performance

    as_user_employee_GetAllChildrenUserId = as_user.employee.GetAllChildrenUserId
    as_user_assign_list = ResourceAssignment.objects.filter(assignee=as_user,deleted=None).values_list('resource__pk',flat=True)
    as_user_employee_TaskAssignedResources = as_user.employee.TaskAssignedResources
    as_user_assign_list_child = ResourceAssignment.objects.filter(assignee__id__in=as_user_employee_GetAllChildrenUserId,deleted=None).values_list('resource__pk',flat=True)
    total_assign_pk = set(as_user_assign_list) | set(as_user_employee_TaskAssignedResources) | set(as_user_assign_list_child)
    

    context={}
    context["op_areas"] = OPArea.objects.all()
    context["op_projects"] = OPProject.objects.all()
    context["resource_id"]=resource_id
    context["tab_id"]=1
    context["consuming_resource_type"]=ResourceType.objects.filter(category=1)    
    context["hardware_resource_type"]=ResourceType.objects.filter(category=2)    
    context["software_resource_type"]=ResourceType.objects.filter(category=3)    
    context["switch_expire_show_consuming"]=False
    context["switch_logical_delete_show_consuming"]=False
    context["switch_hardware_inventory"]=False
    context["switch_hardware_return"]=False
    context["switch_hardware_broken"]=False
    context["switch_hardware_repaired"]=False
    context["switch_hardware_case"]=False
    if resource_id:
        _resource=Resource.objects.get(pk=resource_id)
        context["tab_id"]=_resource.resource_type.category

        try:
            if ConsumingResource.objects.filter(resource=_resource).order_by('-id').first().expiration<datetime.date.today():
                context["switch_expire_show_consuming"]=True
        except:
            context["switch_expire_show_consuming"]=True
    

    _consuming_projects = ConsumingResource.objects.exclude(project = None).values_list('project',flat=True)
    context["consuming_projects"]= set(_consuming_projects)

    consuming_users=[]
    hardware_users=[]
    software_users=[]

    consuming_users.append(as_user.pk)
    hardware_users.append(as_user.pk)
    software_users.append(as_user.pk)

    # rr = ResourceAssignment.objects.filter(Q(resource__owner=as_user,deleted=None)|Q(resource__locumtenens=as_user,deleted=None))
    
    # for r in rr:
    #     if r.resource.resource_type.category==1:
    #         consuming_users.append(r.assignee.pk)
    #     elif r.resource.resource_type.category==2:
    #         hardware_users.append(r.assignee.pk)
    #     elif r.resource.resource_type.category==3:
    #         software_users.append(r.assignee.pk)

    consuming_users += list(ResourceAssignment.objects.filter(resource__resource_type__category=1).filter(Q(resource__owner=as_user,deleted=None)|Q(resource__locumtenens=as_user,deleted=None)).values_list('assignee__pk',flat=True))
    hardware_users += list(ResourceAssignment.objects.filter(resource__resource_type__category=2).filter(Q(resource__owner=as_user,deleted=None)|Q(resource__locumtenens=as_user,deleted=None)).values_list('assignee__pk',flat=True))
    software_users += list(ResourceAssignment.objects.filter(resource__resource_type__category=3).filter(Q(resource__owner=as_user,deleted=None)|Q(resource__locumtenens=as_user,deleted=None)).values_list('assignee__pk',flat=True))
    
    for u in as_user_employee_GetAllChildrenUserId:
        consuming_users.append(u)
        hardware_users.append(u)
        software_users.append(u)
    
    context["consuming_users"]=User.objects.filter(pk__in=consuming_users).order_by('last_name')
    context["hardware_users"]=User.objects.filter(pk__in=hardware_users).order_by('last_name')
    context["software_users"]=User.objects.filter(pk__in=software_users).order_by('last_name')



    _resources_no_expire_id_list= ConsumingResource.objects.filter(expiration__gte=datetime.date.today()).values_list('resource__pk',flat=True)
    _resources_no_expire_id_list = set(_resources_no_expire_id_list)
    if None in _resources_no_expire_id_list:
        _resources_no_expire_id_list.remove(None)
    
    if len(request.GET) == 0:
        _consuming=Resource.objects.filter(
            Q(owner=as_user) |Q(owner__id__in=as_user_employee_GetAllChildrenUserId)|Q(locumtenens=as_user)|Q(locumtenens__id__in=as_user_employee_GetAllChildrenUserId)|
            Q(pk__in=as_user_assign_list)|Q(pk__in=as_user_employee_TaskAssignedResources)|
            Q(pk__in=as_user_assign_list_child) 
            ,resource_type__category=1).annotate(consuming_expiration=Window(
                expression=FirstValue('consuming_resources__expiration'),
                partition_by=[F('consuming_resources__resource__id'),],
                order_by=F('consuming_resources__id').desc()
            )).distinct()
        
        if context["switch_expire_show_consuming"]:
            _consuming=_consuming.exclude(pk__in=_resources_no_expire_id_list)
        else:
            _consuming=_consuming.filter(pk__in=_resources_no_expire_id_list)

        if context["switch_logical_delete_show_consuming"]:
            _consuming=_consuming.filter(deleted=True)
        else:
            _consuming=_consuming.exclude(deleted=True)
    
    _hardware=None        
    if len(request.GET) > 0:
        _hardware=Resource.objects.filter(
            Q(owner=as_user) |Q(owner__id__in=as_user_employee_GetAllChildrenUserId) |Q(locumtenens=as_user)|Q(locumtenens__id__in=as_user_employee_GetAllChildrenUserId)|
            Q(pk__in=total_assign_pk) 
            ,resource_type__category=2).annotate(hardware_code=F('hardware_resource__code'))
    else:
        _hardware=Resource.objects.filter(
            Q(pk__in=as_user_assign_list) 
            ,resource_type__category=2).annotate(hardware_code=F('hardware_resource__code'))
        data={}
        data["resource_filters_user_assignee_hardware"]=request.user.pk
        context["data"]=data

    _software=Resource.objects.filter(
        Q(owner=as_user) |Q(owner__id__in=as_user_employee_GetAllChildrenUserId)|Q(locumtenens=as_user)|Q(locumtenens__id__in=as_user_employee_GetAllChildrenUserId)|
        Q(pk__in=total_assign_pk) 
        ,resource_type__category=3)

    
    if len(request.GET) > 0:
        context["tab_id"]=request.GET["tab_id"]
        context["data"]=request.GET


        if "switch_hardware_inventory" in  request.GET:
            _hardware=_hardware.exclude(pk__in=ResourceAssignment.objects.filter(deleted=None).values('resource__pk'))
            context["switch_hardware_inventory"]=True
        else:
            context["switch_hardware_inventory"]=False

        if "switch_hardware_broken" in  request.GET:
            _hardware=_hardware.exclude(hardware_resource__health = True)
            context["switch_hardware_broken"]=True
        else:
            context["switch_hardware_broken"]=False

        if "switch_hardware_repaired" in  request.GET:
            _hardware=_hardware.filter(hardware_resource__repair = True)
            context["switch_hardware_repaired"]=True
        else:
            context["switch_hardware_repaired"]=False

        if "switch_hardware_return" in  request.GET:
            _hardware=_hardware.filter(hardware_resource__return_status=True)
            context["switch_hardware_return"]=True
        else:
            _hardware=_hardware.filter(hardware_resource__return_status=False)
            context["switch_hardware_return"]=False

        if "switch_hardware_case" in  request.GET:
            _hardware=_hardware.annotate(active_from_relations = Count('from_relations',filter=Q(deleted=None)))
            _hardware=_hardware.filter(active_from_relations = 0)
            context["switch_hardware_case"]=True
        else:
            context["switch_hardware_case"]=False

            
        if "switch_expire_show_consuming" in  request.GET:
            context["switch_expire_show_consuming"]=True
            _consuming=Resource.objects.exclude(pk__in=_resources_no_expire_id_list).filter(
            Q(owner=as_user) |Q(owner__id__in=as_user_employee_GetAllChildrenUserId)|Q(locumtenens=as_user)|Q(locumtenens__id__in=as_user_employee_GetAllChildrenUserId)|
            Q(pk__in=total_assign_pk)
            ,resource_type__category=1).annotate(consuming_expiration=Window(
                expression=FirstValue('consuming_resources__expiration'),
                partition_by=[F('consuming_resources__resource__id'),],
                order_by=F('consuming_resources__id').desc()
            )).distinct()

        else:
            context["switch_expire_show_consuming"]=False
            if "switch_logical_delete_show_consuming" not in request.GET:  
                _consuming=Resource.objects.filter(pk__in=_resources_no_expire_id_list).filter(
                Q(owner=as_user) |Q(owner__id__in=as_user_employee_GetAllChildrenUserId)|Q(locumtenens=as_user)|Q(locumtenens__id__in=as_user_employee_GetAllChildrenUserId)|
                Q(pk__in=total_assign_pk)
                ,resource_type__category=1).annotate(consuming_expiration=Window(
                    expression=FirstValue('consuming_resources__expiration'),
                    partition_by=[F('consuming_resources__resource__id'),],
                    order_by=F('consuming_resources__id').desc()
                )).distinct()


        if "switch_logical_delete_show_consuming" in request.GET:
            context["switch_logical_delete_show_consuming"]=True
            context["switch_expire_show_consuming"]=False  
            _consuming=Resource.objects.filter(deleted=True).filter(
            Q(owner=as_user) |Q(owner__id__in=as_user_employee_GetAllChildrenUserId)|Q(locumtenens=as_user)|Q(locumtenens__id__in=as_user_employee_GetAllChildrenUserId)|
            Q(pk__in=total_assign_pk) 
            ,resource_type__category=1).annotate(consuming_expiration=Window(
                expression=FirstValue('consuming_resources__expiration'),
                partition_by=[F('consuming_resources__resource__id'),],
                order_by=F('consuming_resources__id').desc()
            )).distinct()
        else:
            context["switch_logical_delete_show_consuming"]=False
            _consuming=_consuming.exclude(deleted=True)
        

        #--------------------------------------------------------------------------

        if "resource_filters_resource_type_consuming" in request.GET and int(request.GET["resource_filters_resource_type_consuming"])>0:
            _consuming=_consuming.filter(resource_type__id=int(request.GET["resource_filters_resource_type_consuming"]))

        if "resource_filters_project_consuming" in request.GET and request.GET["resource_filters_project_consuming"] != "همه" and request.GET["resource_filters_project_consuming"] != "-1":
            _resource_id_list=set(list(ConsumingResource.objects.filter(project = request.GET["resource_filters_project_consuming"]).values_list('resource__pk',flat=True)))

            _consuming=_consuming.filter(pk__in=_resource_id_list)

        if "resource_filters_user_assignee_consuming" in request.GET and int(request.GET["resource_filters_user_assignee_consuming"])>0:
            _resource_id_list=list(ResourceAssignment.objects.filter(assignee__id=int(request.GET["resource_filters_user_assignee_consuming"])).values_list('resource__pk',flat=True))
            _consuming=_consuming.filter(pk__in=_resource_id_list)
        
        #--------------------------------------------------------------------------

        if "resource_filters_resource_type_hardware" in request.GET and int(request.GET["resource_filters_resource_type_hardware"])>0:
            _hardware=_hardware.filter(resource_type__id=int(request.GET["resource_filters_resource_type_hardware"]))

        if "resource_filters_organization_group_hardware" in request.GET and int(request.GET["resource_filters_organization_group_hardware"])>0:
            _resource_id_list=list(ResourceAssignment.objects.filter(deleted=None,assignee__employee__organization_group__id=int(request.GET["resource_filters_organization_group_hardware"])).values_list('resource__pk',flat=True))
            _hardware=_hardware.filter(pk__in=_resource_id_list)

        if "resource_filters_user_assignee_hardware" in request.GET and int(request.GET["resource_filters_user_assignee_hardware"])>0:
            _resource_id_list=list(ResourceAssignment.objects.filter(deleted=None,assignee__id=int(request.GET["resource_filters_user_assignee_hardware"])).values_list('resource__pk',flat=True))
            _hardware=_hardware.filter(pk__in=_resource_id_list)

        #--------------------------------------------------------------------------
        if "resource_filters_resource_type_software" in request.GET and int(request.GET["resource_filters_resource_type_software"])>0:
            _software=_software.filter(resource_type__id=int(request.GET["resource_filters_resource_type_software"]))

        if "resource_filters_organization_group_software" in request.GET and int(request.GET["resource_filters_organization_group_software"])>0:
            _resource_id_list=list(ResourceAssignment.objects.filter(assignee__employee__organization_group__id=int(request.GET["resource_filters_organization_group_software"])).values_list('resource__pk',flat=True))
            _software=_software.filter(pk__in=_resource_id_list)

        if "resource_filters_user_assignee_software" in request.GET and int(request.GET["resource_filters_user_assignee_software"])>0:
            _resource_id_list=list(ResourceAssignment.objects.filter(assignee__id=int(request.GET["resource_filters_user_assignee_software"])).values_list('resource__pk',flat=True))
            _software=_software.filter(pk__in=_resource_id_list)
        #--------------------------------------------------------------------------
        if "resource_filters_order_consuming" in request.GET and int(request.GET["resource_filters_order_consuming"])>0:
            _order_kind=int(request.GET["resource_filters_order_consuming"])
            if _order_kind==1:
                _consuming=_consuming.order_by('-id')
            elif _order_kind==2:
                _consuming=_consuming.order_by('id')
            elif _order_kind==3:
                _consuming=_consuming.order_by('resource_type__id')
            elif _order_kind==4:
                _consuming=_consuming.order_by('owner__id')
            elif _order_kind==5:
                _consuming=_consuming.order_by('locumtenens__id')
            elif _order_kind==6:
                _consuming=_consuming.order_by('consuming_expiration')

        if "resource_filters_order_hardware" in request.GET and int(request.GET["resource_filters_order_hardware"])>0:
            _order_kind=int(request.GET["resource_filters_order_hardware"])
            if _order_kind==1:
                _hardware=_hardware.order_by('-id')
            elif _order_kind==2:
                _hardware=_hardware.order_by('id')
            elif _order_kind==3:
                _hardware=_hardware.order_by('resource_type__id')
            elif _order_kind==4:
                _hardware=_hardware.order_by('owner__id')
            elif _order_kind==5:
                _hardware=_hardware.order_by('locumtenens__id')
            elif _order_kind==6:
                _hardware=_hardware.order_by('hardware_code')

        if "resource_filters_order_software" in request.GET and int(request.GET["resource_filters_order_software"])>0:
            _order_kind=int(request.GET["resource_filters_order_software"])
            if _order_kind==1:
                _software=_software.order_by('-id')
            elif _order_kind==2:
                _software=_software.order_by('id')
            elif _order_kind==3:
                _software=_software.order_by('resource_type__id')
            elif _order_kind==4:
                _software=_software.order_by('owner__id')
            elif _order_kind==5:
                _software=_software.order_by('locumtenens__id')

        if "resource_list_search" in request.GET and len(request.GET["resource_list_search"])>0 :
            search_string = request.GET["resource_list_search"]
            search_q = SearchQuery(search_string)
            search_vector = SearchVector('name', weight='A') + SearchVector('description', weight='B')
            _id_list = list(_consuming.values_list('pk', flat = True)) + list(_hardware.values_list('pk', flat = True)) + list(_software.values_list('pk', flat = True))

            filtered_text_res = list(ResourcePropertyText.objects.filter(value__icontains = search_string, resource__id__in = _id_list).values_list('resource__pk',flat=True))
            filtered_date_res = list(ResourcePropertyDate.objects.annotate(nvalue=Cast('value',models.CharField()))\
                .filter(nvalue__icontains = search_string, resource__id__in = _id_list).values_list('resource__pk',flat=True))
            filtered_num_res = list(ResourcePropertyNum.objects.annotate(nvalue=Cast('value',models.CharField()))\
                .filter(nvalue__icontains = search_string, resource__id__in = _id_list).values_list('resource__pk',flat=True))

            filtered_res_prop = filtered_text_res + filtered_date_res + filtered_num_res

            filtered_software = _software.annotate(search = Concat(F('name'),Value(" "),F('description'),Value(" "),F('task__name'),output_field=models.TextField())).filter(search__icontains = search_string)
            if filtered_software.count():
                _software = filtered_software | _software.filter(pk__in=filtered_res_prop).annotate(search=Cast(0,models.TextField()))
            else:
                _software = _software.filter(pk__in=filtered_res_prop).annotate(search=Cast(0,models.TextField()))

            filtered_hardware = _hardware.annotate(search = Concat(F('name'),Value(" "),F('description'),Value(" "),F('task__name'),Value(" "),F('hardware_resource__manufacturer')\
                ,Value(" "),F('hardware_resource__code'),Value(" "),F('hardware_resource__serial'),output_field=models.TextField())).filter(search__icontains = search_string)
            if filtered_hardware.count():
                _hardware = filtered_hardware | _hardware.filter(pk__in=filtered_res_prop).annotate(search=Cast(0,models.TextField()))
            else :
                _hardware = _hardware.filter(pk__in=filtered_res_prop).annotate(search=Cast(0,models.TextField()))

            filtered_consuming = _consuming.annotate(search = Concat(F('name'),Value(" "),F('description'),Value(" "),F('task__name'),output_field=models.TextField())).filter(search__icontains = search_string)
            if filtered_consuming.count():
                _consuming = filtered_consuming | _consuming.filter(pk__in=filtered_res_prop).annotate(search=Cast(0,models.TextField()))
            else:
                _consuming = _consuming.filter(pk__in=filtered_res_prop).annotate(search=Cast(0,models.TextField()))

    context["consuming_resources"]=_consuming.only('id','name','resource_type').prefetch_related('assignements').select_related('resource_type')
    context["hardware_resources"]=_hardware.only('id','name','resource_type').prefetch_related('assignements',\
        Prefetch('resource_num_properties',queryset=ResourcePropertyNum.objects.filter(Q(resource_type_property__name__contains='تعداد')|\
            Q(resource_type_property__slug__contains='tedad')),to_attr='count_property'))\
                        .select_related('resource_type').select_related('hardware_resource')
    context["software_resources"]=_software.only('id','name','resource_type').prefetch_related('assignements').select_related('resource_type')

    context["hardware_resources_owner_access"] = False

    h_resources = HardwareResource.objects.all().values_list("resource_id", flat=True)
    h_resource_owners = Resource.objects.filter(id__in=h_resources).values_list("owner_id", flat=True)
    if request.user.id in h_resource_owners or len( set(request.user.employee.GetAllChildrenUserId) & set(h_resource_owners) ) > 0 :
        context["hardware_resources_owner_access"] = True
    
    return render(request, 'resource/list.html', {'context':context})

@login_required(login_url='user:login') #redirect when user is not logged in
def GetResourceTypeProperty(request,resource_type):
    context={}
    try:
        context["resource_type"]=serializers.serialize('json',ResourceTypeProperty.objects.filter(resource_type__id=resource_type))
    except:
        pass
    return  JsonResponse(context)

@login_required(login_url='user:login') #redirect when user is not logged in
def GetResourceTypePropertyValue(request,resource_id):
    if len(request.user.locumtenens_organization_groups.all())>0 and request.user.locumtenens_organization_groups.first().locumtenens_active:
        as_user = request.user.locumtenens_organization_groups.first().manager
    else:
        as_user = request.user

    context={}
    try:
        _resource=Resource.objects.get(pk=resource_id)
        if not(_resource.owner == as_user or _resource.locumtenens == as_user or _resource.creator== as_user or as_user.id in _resource.creator.employee.GetEmployeeParentSet or as_user.id in _resource.owner.employee.GetEmployeeParentSet or as_user.id in _resource.locumtenens.employee.GetEmployeeParentSet or _resource.id in as_user.employee.TaskAssignedResources):
            raise PermissionDenied
        resource_property_num=ResourcePropertyNumSerializer(ResourcePropertyNum.objects.filter(resource__id=resource_id), many=True)
        context["resource_property_num"]=JSONRenderer().render(resource_property_num.data).decode("utf-8")

        resource_property_text=ResourcePropertyTextSerializer(ResourcePropertyText.objects.filter(resource__id=resource_id), many=True)
        context["resource_property_text"]=JSONRenderer().render(resource_property_text.data).decode("utf-8")

        resource_property_file=ResourcePropertyFileSerializer(ResourcePropertyFile.objects.filter(resource__id=resource_id), many=True)
        context["resource_property_file"]=JSONRenderer().render(resource_property_file.data).decode("utf-8")

        resource_property_bool=ResourcePropertyBoolSerializer(ResourcePropertyBool.objects.filter(resource__id=resource_id), many=True)
        context["resource_property_bool"]=JSONRenderer().render(resource_property_bool.data).decode("utf-8")

        resource_property_date=ResourcePropertyDateSerializer(ResourcePropertyDate.objects.filter(resource__id=resource_id), many=True)
        context["resource_property_date"]=JSONRenderer().render(resource_property_date.data).decode("utf-8")
    except:
        pass
    return  JsonResponse(context)

@login_required(login_url='user:login') #redirect when user is not logged in
def GetResourceDetails(request,resource_id):
    if len(request.user.locumtenens_organization_groups.all())>0 and request.user.locumtenens_organization_groups.first().locumtenens_active:
        as_user = request.user.locumtenens_organization_groups.first().manager
    else:
        as_user = request.user

    context={}

    # try:
    _resource=Resource.objects.all().select_related('creator','owner','locumtenens','resource_type','task','hardware_resource')\
        .prefetch_related(Prefetch('assignements',queryset=ResourceAssignment.objects.filter(deleted=None)))\
            .prefetch_related(Prefetch('assignements',queryset=ResourceAssignment.objects.all(), to_attr='all_assignements'))\
                .prefetch_related('assignements__assignee').prefetch_related('task_assignement__task')\
                    .prefetch_related(Prefetch('consuming_resources', queryset=ConsumingResource.objects.all().order_by('-pk')))\
                        .prefetch_related('resource_num_properties')\
                            .prefetch_related(Prefetch('resource_num_properties', queryset=ResourcePropertyNum.objects.filter(resource_type_property__isPublic=True), to_attr='public_resource_num_properties'))\
                                .prefetch_related('resource_text_properties')\
                                    .prefetch_related(Prefetch('resource_text_properties', queryset=ResourcePropertyText.objects.filter(resource_type_property__isPublic=True), to_attr='public_resource_text_properties'))\
                                        .prefetch_related('resource_file_properties')\
                                            .prefetch_related(Prefetch('resource_file_properties', queryset=ResourcePropertyFile.objects.filter(resource_type_property__isPublic=True), to_attr='public_resource_file_properties'))\
                                                .prefetch_related('resource_bool_properties')\
                                                    .prefetch_related(Prefetch('resource_bool_properties', queryset=ResourcePropertyBool.objects.filter(resource_type_property__isPublic=True), to_attr='public_resource_bool_properties'))\
                                                        .prefetch_related('resource_date_properties')\
                                                            .prefetch_related(Prefetch('resource_date_properties', queryset=ResourcePropertyDate.objects.filter(resource_type_property__isPublic=True), to_attr='public_resource_date_properties'))\
                                                                .get(pk=resource_id)
    
    resources_pk=[r["resource__pk"] for r in ResourceAssignment.objects.filter(resource=_resource,deleted=None).filter(Q(assignee=as_user)|Q(assignee__id__in=as_user.employee.GetAllChildrenUserId)).values('resource__pk')]
    
    if (_resource.id in resources_pk or _resource.id in as_user.employee.TaskAssignedResources or _resource.owner == as_user or _resource.locumtenens == as_user   or  _resource.owner.id in  as_user.employee.GetAllChildrenUserId  or (_resource.locumtenens and _resource.locumtenens.id in as_user.employee.GetAllChildrenUserId ) or _resource.id in as_user.employee.TaskAssignedResources):
       
        resource=ResourceSerializer(_resource)
        context["resource"] = JSONRenderer().render(resource.data).decode("utf-8")

        resource_assignment=ResourceAssignmentSerializer(_resource.assignements, many=True)
        context["resource_assignment"] = JSONRenderer().render(resource_assignment.data).decode("utf-8")

        all_resource_assignment=ResourceAssignmentSerializer(_resource.all_assignements, many=True)
        context["all_resource_assignment"] = JSONRenderer().render(all_resource_assignment.data).decode("utf-8")

        consuming_resources=ConsumingResourceSerializer(_resource.consuming_resources.all().order_by("-expiration"), many=True)
        context["consuming_resource"]=JSONRenderer().render(consuming_resources.data).decode("utf-8")

        try:
            hardware_resource=HardwareResourceSerializer(_resource.hardware_resource)
            context["hardware_resource"]=JSONRenderer().render(hardware_resource.data).decode("utf-8")
        except:
            context["hardware_resource"]='[]'

        resource_task = ResourceTaskSerializer(_resource.task_assignement, many=True)
        context["resource_task"]=JSONRenderer().render(resource_task.data).decode("utf-8")
        
        if (_resource.owner == as_user or (_resource.locumtenens and _resource.locumtenens == as_user) or as_user.id in _resource.owner.employee.GetEmployeeParentSet\
            or (_resource.locumtenens and as_user.id in _resource.locumtenens.employee.GetEmployeeParentSet)):
            resource_property_num=ResourcePropertyNumSerializer(_resource.resource_num_properties, many=True)
            context["resource_property_num"]=JSONRenderer().render(resource_property_num.data).decode("utf-8")

            resource_property_text=ResourcePropertyTextSerializer(_resource.resource_text_properties, many=True)
            context["resource_property_text"]=JSONRenderer().render(resource_property_text.data).decode("utf-8")

            resource_property_file=ResourcePropertyFileSerializer(_resource.resource_file_properties, many=True)
            context["resource_property_file"]=JSONRenderer().render(resource_property_file.data).decode("utf-8")

            resource_property_bool=ResourcePropertyBoolSerializer(_resource.resource_bool_properties, many=True)
            context["resource_property_bool"]=JSONRenderer().render(resource_property_bool.data).decode("utf-8")

            resource_property_date=ResourcePropertyDateSerializer(_resource.resource_date_properties, many=True)
            context["resource_property_date"]=JSONRenderer().render(resource_property_date.data).decode("utf-8")
        else:
            resource_property_num=ResourcePropertyNumSerializer(_resource.public_resource_num_properties, many=True)
            context["resource_property_num"]=JSONRenderer().render(resource_property_num.data).decode("utf-8")

            resource_property_text=ResourcePropertyTextSerializer(_resource.public_resource_text_properties, many=True)
            context["resource_property_text"]=JSONRenderer().render(resource_property_text.data).decode("utf-8")

            resource_property_file=ResourcePropertyFileSerializer(_resource.public_resource_file_properties, many=True)
            context["resource_property_file"]=JSONRenderer().render(resource_property_file.data).decode("utf-8")

            resource_property_bool=ResourcePropertyBoolSerializer(_resource.public_resource_bool_properties, many=True)
            context["resource_property_bool"]=JSONRenderer().render(resource_property_bool.data).decode("utf-8")

            resource_property_date=ResourcePropertyDateSerializer(_resource.public_resource_date_properties, many=True)
            context["resource_property_date"]=JSONRenderer().render(resource_property_date.data).decode("utf-8")
        
    else:
        raise PermissionDenied
    # except:
    #     pass
    return  JsonResponse(context)

@login_required(login_url='user:login') #redirect when user is not logged in
def Delete(request,resource_id):
    try:
        resource=Resource.objects.get(pk=resource_id)
        if not(resource.owner == request.user): # or resource.creator== request.user or resource.creator.employee.GetEmployeeParent== request.user.id or resource.owner.employee.GetEmployeeParent== request.user.id):
            raise PermissionDenied
        
        for assigner in ResourceAssignment.objects.filter(resource=resource,deleted=None):
            try:
                notification=Notification.objects.get(pk=assigner.assignee_notification.pk)
                notification.delete()
            except:
                pass
        try:
            notification=Notification.objects.get(pk=resource.expire_notification.pk)
            notification.delete()
        except:
            pass
        resource.delete()
        
        return HttpResponse("True")
    except:
        return HttpResponse("False")

@login_required(login_url='user:login') #redirect when user is not logged in
def LogicalDelete(request,resource_id):
    try:
        resource=Resource.objects.get(pk=resource_id)
        if not(resource.owner == request.user):
            raise PermissionDenied
        

        resource.deleted=True     # غیر قابل تمدید
        resource.save()
        
        return HttpResponse("True")
    except:
        return HttpResponse("False")

@login_required(login_url='user:login') #redirect when user is not logged in
def AddNewConsumingResource(request):
    if len(request.user.locumtenens_organization_groups.all())>0 and request.user.locumtenens_organization_groups.first().locumtenens_active:
        as_user = request.user.locumtenens_organization_groups.first().manager
    else:
        as_user = request.user

    context={}
    try:
        if request.method == "POST":
            resource=Resource.objects.get(pk=int(request.POST["consuming_resource_pk"]))
            if resource.owner != as_user and resource.locumtenens != as_user and as_user.id not in resource.owner.employee.GetEmployeeParentSet and not(resource.locumtenens and as_user.id in resource.locumtenens.employee.GetEmployeeParentSet):
                raise PermissionDenied
            consuming_resource=ConsumingResource()
            consuming_resource.resource=resource
            if(request.POST["consuming_resource_price"]):
                consuming_resource.price=decimal.Decimal(request.POST["consuming_resource_price"])
            else:
                consuming_resource.price=0

            # if(request.POST["consuming_resource_project"]):
            #     consuming_resource.project=request.POST["consuming_resource_project"]
            # else:
            #     consuming_resource.project=consuming_resource.resource.consuming_resources.all().latest().project

            if request.POST["consuming_resource_op_project"] and int(request.POST["consuming_resource_op_project"]) > 0:
                consuming_resource.op_project_id=request.POST["consuming_resource_op_project"]
            elif request.POST["consuming_resource_op_project"] and int(request.POST["consuming_resource_op_project"]) == 0:
                consuming_resource.op_project = None
            else:
                consuming_resource.op_project=consuming_resource.resource.consuming_resources.all().latest().op_project

            if request.POST["consuming_resource_op_area"] and int(request.POST["consuming_resource_op_area"]) > 0:
                consuming_resource.op_area_id=request.POST["consuming_resource_op_area"]
            else:
                consuming_resource.op_area=consuming_resource.resource.consuming_resources.all().latest().op_area

            if(request.POST["consuming_resource_total_amount"]):
                consuming_resource.total_amount=decimal.Decimal(request.POST["consuming_resource_total_amount"])
            else:
                consuming_resource.total_amount=0

            if(request.POST["consuming_resource_consumed_amount"]):
                consuming_resource.consumed_amount=decimal.Decimal(request.POST["consuming_resource_consumed_amount"])
            else:
                consuming_resource.consumed_amount=0

            if(request.POST["consuming_resource_expiration"]):
                consuming_resource.expiration=ConvertToMiladi(request.POST["consuming_resource_expiration"])
            else:
                consuming_resource.expiration=""
            if (not request.POST["consuming_resource_expiration"] and not request.POST["consuming_resource_total_amount"]):
                context["message"] = "یکی از فیلدهای تاریخ انقضاء و حجم کل باید مقدار دهی شود"
                context["status"]=False
            else:
                context["status"]=True
                context["message"] = "عملیات با موفقیت انجام شد"
                consuming_resource.save()

                #----------------Notification for expire
                notification=Notification()
                if resource.expire_notification:
                    notification=Notification.objects.get(pk=resource.expire_notification.pk)
                notification.title="انقضاء منبع"
                notification.user=resource.owner
                notification.displaytime =  datetime.datetime.strptime(consuming_resource.expiration,'%Y-%m-%d') - datetime.timedelta(days=4)
                notification.messages="منبع "+ resource.name +" در تاریخ "+ ConvertToSolarDate(consuming_resource.expiration) +" منقضی می شود"
                notification.link="/resource/"+str(resource.pk)+"/list/"
                notification.closed=False
                notification.save()
                #----------------Notification
                resource.expire_notification=notification
                resource.save()
    except:
        context["message"] = "بروز خطا"
        context["status"]=False
    return  JsonResponse(context)

@login_required(login_url='user:login') #redirect when user is not logged in
def GetResourceRelations(request,resource_id,resource_type_id,mode):
    if len(request.user.locumtenens_organization_groups.all())>0 and request.user.locumtenens_organization_groups.first().locumtenens_active:
        as_user = request.user.locumtenens_organization_groups.first().manager
    else:
        as_user = request.user

    context={}


    if resource_id!="None":
        resource=Resource.objects.get(pk=resource_id)
        resources_pk=[r["resource__pk"] for r in ResourceAssignment.objects.filter(resource=resource).filter(Q(assignee=as_user)|Q(assignee__id__in=as_user.employee.GetAllChildrenUserId)).values('resource__pk')]
        if not(int(resource.id) in resources_pk or resource.owner == as_user or resource.locumtenens == as_user  or resource.creator== as_user or resource.creator.id in as_user.employee.GetAllChildrenUserId or  resource.owner.id in  as_user.employee.GetAllChildrenUserId  or (resource.locumtenens and resource.locumtenens.id in as_user.employee.GetAllChildrenUserId ) or resource.id in as_user.employee.TaskAssignedResources):
            raise PermissionDenied

    # if request.user not in ResourceType.objects.get(pk=resource_type_id).creation_limits.all():
    #     raise PermissionDenied
    
    # Mode guide
    # In each mode only some information will be returned
    # 1: For resource edit
    #   returns resource_type_relation, resources, relations
    # 2: For resource add
    #   returns resource_type_relation, resources
    # 3: For resource detail in resources page
    #   returns resource_type_relation,resources,relations,resource_type_relation_reverse,resources_reverse,relations_reverse


    resources=ResourceMiniSerializer(\
        Resource.objects.filter(resource_type__in=ResourceTypeRelation.objects.filter(source_resource_type__id=resource_type_id).values('destinaton_resource_type')), many=True)
    context["resources"] = JSONRenderer().render(resources.data).decode("utf-8")

    resource_type_relation = ResourceTypeRelationMiniSerializer(\
        ResourceTypeRelation.objects.filter(source_resource_type__id=resource_type_id).order_by('order'), many=True)
    context["resource_type_relation"] = JSONRenderer().render(resource_type_relation.data).decode("utf-8")

    if mode == 1 or mode ==3:
        if resource_id!="None":
            relations = ResourceRelationMiniSerializer(\
                ResourceRelation.objects.filter(source_resource__id=resource_id,deleted=None), many= True)
            context["relations"]=JSONRenderer().render(relations.data).decode("utf-8")

    
    if mode == 3 :
        resource_type_relation_reverse = ResourceTypeRelationMiniSerializer(\
            ResourceTypeRelation.objects.filter(destinaton_resource_type__id=resource_type_id).order_by('order'), many=True)
        context["resource_type_relation_reverse"] = JSONRenderer().render(resource_type_relation_reverse.data).decode("utf-8")    
        
        resources=ResourceMiniSerializer(\
            Resource.objects.filter(resource_type__in=ResourceTypeRelation.objects.filter(destinaton_resource_type__id=resource_type_id).values('source_resource_type')), many=True)
        context["resources_reverse"] = JSONRenderer().render(resources.data).decode("utf-8")
        if resource_id!="None":
            relations_reverse = ResourceRelationMiniSerializer(\
                ResourceRelation.objects.filter(destinaton_resource__id=resource_id,deleted=None), many= True)
            context["relations_reverse"]=JSONRenderer().render(relations_reverse.data).decode("utf-8")

    return  JsonResponse(context)

@login_required(login_url='user:login') #redirect when user is not logged in
def SaveAssigneeDescription(request,resource_id):
    context={}
    try:
        resource_assignement=ResourceAssignment.objects.get(resource__id=resource_id,assignee=request.user,deleted=None)
        if resource_assignement and request.method == "POST":
            resource_assignement.description=request.POST["description"]
            resource_assignement.save()
            context["message"]='توضیحات مسئول با موفقیت ذخیره شد'
    except:
        context["message"]='عملیات با خطا مواجه شد'

    return  JsonResponse(context)

@login_required(login_url='user:login') #redirect when user is not logged in
def ExportSoftwarereSources(request):
    pass

@login_required(login_url='user:login') #redirect when user is not logged in
def ExportHardwareResources(request):
    context={}
    _user = request.user
    try:
        if request.method == "POST":
            if "resource_list_hardware_export_input" in request.POST:
                resourceIDsStr = request.POST["resource_list_hardware_export_input"]
                excel_name = request.POST.get("download_name",None)
                if "," in resourceIDsStr:
                    resourceIDsStr = resourceIDsStr.split(",")
                else: 
                    resourceIDsStr = [resourceIDsStr]
                resourceIDs = []
                for i in resourceIDsStr:
                    resourceIDs.append(int(i))
                excel_title=["شناسه" , "کد" , "نام" ,"نوع", "امین اموال" , "مسئول" , "تعداد" ]
                resource_list = []
                resource_list.append(excel_title)
                resource = Resource.objects.filter(pk__in = resourceIDs).prefetch_related('assignements',\
                    Prefetch('resource_num_properties',queryset=ResourcePropertyNum.objects.filter(Q(resource_type_property__name__contains='تعداد')|\
                        Q(resource_type_property__slug__contains='tedad')),to_attr='count_property'))

                for r in resource:
                    resource_assignee = ResourceAssignment.objects.filter(resource = r,deleted=None).last()
                    if _user != r.owner and resource_assignee and _user != resource_assignee.assignee and _user != r.locumtenens and _user.id not in r.owner.employee.GetEmployeeParentSet and _user.id not in resource_assignee.assignee.employee.GetEmployeeParentSet and _user.id not in r.locumtenens.employee.GetEmployeeParentSet:
                        raise PermissionDenied
                    if _user != r.owner and  not resource_assignee  and _user != r.locumtenens and _user.id not in r.owner.employee.GetEmployeeParentSet  and _user.id not in r.locumtenens.employee.GetEmployeeParentSet:
                        raise PermissionDenied
                    r_id = r.id
                    r_type = r.resource_type.name
                    r_name = r.name
                    if not r.hardware_resource.health:
                        r_name +="(خراب)"
                    if r.hardware_resource.repair:
                        r_name +="(تعمیر شده)"
                    r_owner = r.owner.get_full_name()
                    if resource_assignee and resource_assignee.assignee:
                        r_assignee = resource_assignee.assignee.get_full_name()
                    else:
                        r_assignee="انبار"
                    r_code = r.HardwareResourceCode
                    r_type = r.resource_type.name
                    r_count = 1
                    if len(r.count_property) > 0:
                        r_count = int(r.count_property[0].value)
                    resource_record = [r_id , r_code , r_name ,r_type , r_owner , r_assignee , r_count]
                    resource_list.append(resource_record)

                    if r.resource_type.slug == "case":
                        for sub_res_rel in r.to_relations.all().filter(deleted = None):
                            sub_res = Resource.objects.filter(id = sub_res_rel.source_resource.id).prefetch_related('assignements',\
                                Prefetch('resource_num_properties',queryset=ResourcePropertyNum.objects.filter(Q(resource_type_property__name__contains='تعداد')|\
                                    Q(resource_type_property__slug__contains='tedad')),to_attr='count_property')).first()
                            resource_assignee = ResourceAssignment.objects.filter(resource = sub_res,deleted=None).last()
                            if _user != sub_res.owner and resource_assignee and _user != resource_assignee.assignee and _user != sub_res.locumtenens and _user.id not in sub_res.owner.employee.GetEmployeeParentSet and _user.id not in resource_assignee.assignee.employee.GetEmployeeParentSet and _user.id not in sub_res.locumtenens.employee.GetEmployeeParentSet:
                                raise PermissionDenied
                            if _user != sub_res.owner and  not resource_assignee  and _user != sub_res.locumtenens and _user.id not in sub_res.owner.employee.GetEmployeeParentSet  and _user.id not in sub_res.locumtenens.employee.GetEmployeeParentSet:
                                raise PermissionDenied
                            r_id = str(sub_res.id) + "-"
                            r_type = sub_res.resource_type.name
                            r_name = sub_res.name
                            if not sub_res.hardware_resource.health:
                                r_name +="(خراب)"
                            if sub_res.hardware_resource.repair:
                                r_name +="(تعمیر شده)"
                            r_owner = sub_res.owner.get_full_name()
                            if resource_assignee and resource_assignee.assignee:
                                r_assignee = resource_assignee.assignee.get_full_name()
                            else:
                                r_assignee="انبار"
                            r_code = sub_res.HardwareResourceCode
                            r_type = sub_res.resource_type.name
                            r_count = 1
                            if len(sub_res.count_property) > 0:
                                r_count = int(sub_res.count_property[0].value)
                            resource_record = [r_id , r_code , r_name ,r_type , r_owner , r_assignee , r_count]
                            resource_list.append(resource_record)

                    
            wb = Workbook()
            sheet = wb.active
            sheet.title = "اموال"
            sheet.column_dimensions["A"].width = 10
            sheet.column_dimensions["B"].width = 20
            sheet.column_dimensions["C"].width = 20
            sheet.column_dimensions["D"].width = 20
            sheet.column_dimensions["E"].width = 20
            sheet.column_dimensions["F"].width = 20
            sheet.column_dimensions["G"].width = 20
            sheet.sheet_view.rightToLeft = True

            m = 0
            for i in resource_list:
                m += 1
                n=0
                for j in i:
                    n += 1
                    a = sheet.cell (row=m , column=n ) 
                    a.value = j


            response = HttpResponse( content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" , )
            if excel_name == None or excel_name =="":
                response["Content-Disposition"] = "attachment;filename=report-{date}.xlsx".format(date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),)
            else:
                response["Content-Disposition"] = "attachment;filename="+ excel_name +".xlsx"

            wb.save(response)

    except Exception as ex:
        response=HttpResponse("عملیات با خطا مواجه شد")
    return  response

@login_required(login_url='user:login') #redirect when user is not logged in
def ExportConsumingResources(request):
    if not request.user.is_superuser :
        return HttpResponse("َشما دسترسی انجام این عملیات را ندارید")
    r_id = 0
    try:
        excel_name = request.POST.get("download_name",None)
        
        excel_title=[ "کد" , "عنوان" ,"نوع", "انقظا" , "مسئول" , "پروژه" , "غیر قابل تمدید"]
        resource_list = []
        resource_list.append(excel_title)
        resource=Resource.objects.filter(resource_type__category=1)

        for r in resource:
            resource_assignee = ResourceAssignment.objects.filter(resource = r,deleted=None).last()
            r_id = r.id
            r_name = r.name
            r_type = r.resource_type.name
            r_expire = r.ConsumingResourcePersianExpiration
            r_project = ""
            if r.consuming_resources.count() and r.consuming_resources.latest().op_area:
                r_project += r.consuming_resources.latest().op_area.name
                if r.consuming_resources.latest().op_project: 
                    r_project += "-" + r.consuming_resources.latest().op_project.name

            if resource_assignee and resource_assignee.assignee:
                r_assignee = resource_assignee.assignee.get_full_name()
            else:
                r_assignee="-"

            if r.deleted:
                r_deleted = "بله"
            else:
                r_deleted = "خیر"
            
            resource_record = [r_id , r_name ,r_type , r_expire , r_assignee , r_project, r_deleted]
            resource_list.append(resource_record)


                
        wb = Workbook()
        sheet = wb.active
        sheet.title = "منابع مصرفی"
        sheet.column_dimensions["A"].width = 10
        sheet.column_dimensions["B"].width = 20
        sheet.column_dimensions["C"].width = 20
        sheet.column_dimensions["D"].width = 20
        sheet.column_dimensions["E"].width = 20
        sheet.column_dimensions["F"].width = 20
        sheet.column_dimensions["G"].width = 20
        sheet.sheet_view.rightToLeft = True

        m = 0
        for i in resource_list:
            m += 1
            n=0
            for j in i:
                n += 1
                a = sheet.cell (row=m , column=n ) 
                a.value = j


        response = HttpResponse( content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" , )
        if excel_name == None or excel_name =="":
            response["Content-Disposition"] = "attachment;filename=report-{date}.xlsx".format(date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),)
        else:
            response["Content-Disposition"] = "attachment;filename="+ excel_name +".xlsx"

        wb.save(response)

    except Exception as ex:
        response=HttpResponse("عملیات با خطا مواجه شد" + str(ex) + str(r_id))
    return  response

@login_required(login_url='user:login') #redirect when user is not logged in
def GetAllRelationsOfResource(request,resource_id):
    context={}
    resource_relation=ResourceRelationSerializer(ResourceRelation.objects.filter(destinaton_resource__id=resource_id,deleted=None), many=True)
    
    context["relations"]=JSONRenderer().render(resource_relation.data).decode("utf-8")
    return  JsonResponse(context)


@login_required(login_url='user:login') #redirect when user is not logged in
def GetAllTaskOfResourceType(request,resource_type):
    context={}
    try:
        tasks=Task.objects.filter(task_type__resource_type__pk=resource_type,progress__gte=0,progress__lt=100,user_assignee=request.user)
        _tasks={}
        for t in tasks:
            _tasks[t.pk]=t.name
        context["tasks"]=_tasks
    except:
        context["tasks"]={}
    return  JsonResponse(context)

@login_required(login_url='user:login') #redirect when user is not logged in
def CheckHardwareCodeReplicated(request,resource_id,code):
    context={}
    context["status"]=False
    try:
        _hardware=HardwareResource.objects.filter(code=code)
        if resource_id and _hardware:
            _hardware=_hardware.exclude(resource__pk=resource_id)
        if _hardware and len(_hardware)>0:
            context["status"]=True
    except:
        context["status"]=False
    return  JsonResponse(context)