from django.db.models import Q ,Sum,ExpressionWrapper,F,DurationField,Count,Min,Max,Window
from django.shortcuts import render, redirect
from django.http import HttpResponse, Http404,HttpResponseRedirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from django.contrib.auth.models import User
from ...models import Task, Task_Level, Task_Type, Task_Attachment, Task_Group, Task_Assign_Request,Task_Prerequisite,PublicTask,TempTimingRecord,PublicTaskTime,TaskTime,Report,Notification,Task_Group_Member, TaskProgress, TaskComment ,ResourcePropertyFile ,ResourcePropertyText
from ...models import Task_Verification_Log,Task_Type_Verification,Task_Type_Auto_Request,Task_Property_Bool,\
    Task_Type_Property,Task_Property_Num,Task_Property_Text,Task_Property_File,Task_Property_Date,Organization_Group\
        ,Employee,Resource,ResourceTaskAssignment,ResourceAssignment, ReportAttachment, Feedback
from ...utilities.date_tools import ConvertToMiladi, ConvertToSolarDate,DateTimeDifference,ConvertTimeDeltaToStringTime
from django.core import serializers
from django.http import JsonResponse
from django.core.exceptions import PermissionDenied
from ...Serializers.task_management_serializer import Task_Type_Auto_RequestSerializer,TaskSerializer,Task_Type_PropertySerializer,Task_DetailSerializer,\
    Task_Property_NumSerializer,Task_Property_TextSerializer,Task_Property_DateSerializer,Task_Property_FileSerializer,TaskCommentReplySerializer,\
        Task_Property_BoolSerializer,TaskRequestSerializer
from rest_framework.renderers import JSONRenderer
import datetime,decimal
import jdatetime as jdt
from sorl.thumbnail import get_thumbnail,delete
import math


def getchildren(id,task_list):
    task = task_list.get(pk=id)
    #tasks = Task.objects.filter(task_parent_id=id).filter(
    #        Q(user_assignee=user)| Q(group_assignee__head=user)|Q(user_assignee__id__in=user.employee.GetAllChildrenUserId)| Q(group_assignee__head__id__in=user.employee.GetAllChildrenUserId)).exclude(cancelled=True).exclude(confirmed=True)
    tasks=task_list.filter(task_parent_id=id)
    s = "<li  class='nodes' id=" + \
        str(task.pk)+"><span class='caret'>"+str(task.name).replace("<","&lt;").replace(">","&gt;") +"</span>"
    if len(tasks) > 0:
        s += "<ul class='nested'>"
        for ch in tasks:
            s += getchildren(ch.pk, task_list)
        s += "</ul>"
    s += "</li>"
    return (s)

# redirect when user is not logged in
@login_required(login_url='user:login')
def Add(request):
    request.session["activated_menu"]="task_add"
    context = {}
    if request.method == "POST":
        context["task"] = request.POST
        context["task_type"] = int(request.POST["task_type"])
        context["task_level"] = int(request.POST["task_level"])
        context["task_parent"] = int(request.POST["task_parent"])
        
        try:
            _hasError = False
            with transaction.atomic():
                task = Task()
                try:
                    if len(request.user.locumtenens_organization_groups.all())>0 and request.user.locumtenens_organization_groups.first().locumtenens_active:
                        as_user = User.objects.get(pk=int(request.POST['as_user'])) if (request.POST['as_user'] and (int(request.POST['as_user']) > 0) and User.objects.get(pk=int(request.POST['as_user'])) and (request.user.locumtenens_organization_groups.first().manager.id in User.objects.get(pk=int(request.POST['as_user'])).employee.GetEmployeeParentSet)) else request.user
                    else:
                        as_user = User.objects.get(pk=int(request.POST['as_user'])) if (request.POST['as_user'] and (int(request.POST['as_user']) > 0) and User.objects.get(pk=int(request.POST['as_user'])) and (request.user.id in User.objects.get(pk=int(request.POST['as_user'])).employee.GetEmployeeParentSet)) else request.user

                except:
                    as_user = request.user

                if request.POST["name"]:
                    task.name = request.POST["name"]
                else:
                    _hasError = True
                    context["Error"] = "فیلد عنوان کار باید مقدار دهی شود"
                if not _hasError:
                    if int(request.POST["task_parent"]) > 0:
                        _tasks = Task.objects.filter(
                            name=request.POST["name"], task_parent_id=0)
                    else:
                        if as_user.employee.GetEmployeeParent:
                            context["Error"] = "فیلد والد باید مقدار دهی شود"
                            _hasError = True
                            _tasks=[]
                        else:
                            _tasks = Task.objects.filter(
                                name=request.POST["name"], task_parent_id=None)
                    if (len(_tasks) > 0):
                        context["Error"] = "فیلدهای عنوان کار نسبت به والد باید یکتا باشد"
                        _hasError = True
                if not _hasError:
                    if int(request.POST["task_level"]) > 0:
                        task.task_level = Task_Level.objects.get(
                            pk=int(request.POST["task_level"]))
                    else:
                        context["Error"] = "فیلد سطح کار باید مقدار دهی شود"
                        _hasError = True
                
                if not _hasError:
                    if int(request.POST["task_parent"]) > 0 and int(request.POST["assign_status"]) != 1  :
                        _parent = Task.objects.get(pk=request.POST["task_parent"])
                        if _parent.group_assignee or _parent.UnderTaskGroup :
                            if int(request.POST["task_type"]) > 0:
                                task.task_type = Task_Type.objects.get(pk=request.POST["task_type"])
                                if (not task.task_type.auto_requests.all().count()>0) :
                                    context["Error"] = "اجازه انتخاب کارگروه و یا ثبت درخواست وجود ندارد"
                                    _hasError = True
                            else:
                                context["Error"] = "اجازه انتخاب کارگروه و یا ثبت درخواست وجود ندارد"
                                _hasError = True

                    if int(request.POST["task_parent"]) > 0 and int(request.POST["assign_status"]) == 1:
                        _parent = Task.objects.get(pk=request.POST["task_parent"])
                        if _parent.group_assignee:
                            _user_assignee = User.objects.get(pk=int(request.POST["assign_key"]))
                            
                            _members=[member.user for member in Task_Group_Member.objects.filter(group=_parent.group_assignee)]
                            if ( _user_assignee!=_parent.group_assignee.head and _user_assignee not in _members):
                                context["Error"] = "مسئول انتخابی مجاز نمی باشد"
                                _hasError = True

                        elif _parent.UnderTaskGroup:
                            _user_assignee = User.objects.get(pk=int(request.POST["assign_key"]))
                            _members=[member.user for member in Task_Group_Member.objects.filter(group=_parent.UnderTaskGroup)]

                            if (as_user ==_parent.UnderTaskGroup.head and _user_assignee!=_parent.UnderTaskGroup.head and _user_assignee not in _members):
                                context["Error"] = "مسئول انتخابی مجاز نمی باشد"
                                _hasError = True
                            elif(as_user !=_parent.UnderTaskGroup.head and _user_assignee!=as_user ):
                                context["Error"] = "مسئول انتخابی مجاز نمی باشد"
                                _hasError = True

            
                if not _hasError and int(request.POST["task_type"]) > 0:
                    task.task_type = Task_Type.objects.get(
                        pk=request.POST["task_type"])
                    if (task.task_type.froce_assign_request and not task.task_type.auto_request) :
                        context["Error"] = " این نوع کار در ثبت درخواست خودکار دچار مشکل است با مدیر سامانه تماس بگیرید"
                        _hasError = True
                    
                    if (not _hasError and task.task_type and task.task_type.needs_verfication) :
                        task_type_verification=Task_Type_Verification.objects.filter(task_type=task.task_type).order_by('order')
                        if task_type_verification.count()==0:
                            context["Error"] = " این نوع کار در ثبت تائیدیه درخواست دچار مشکل است با مدیر سامانه تماس بگیرید"
                            _hasError = True
                        if not _hasError:
                            request_user_key=request.POST["assign_key"].strip().split(",")
                            task_type_auto_request=task.task_type.auto_requests.all()
                            if (len(request_user_key)==0 and request_user_key[0].strip() == '' ) and task_type_auto_request.count()==0 :
                                context["Error"] = "کاربر مورد درخواست نامشخص است"
                                _hasError = True
                    else:
                        if (not _hasError and task.task_type and task.task_type.auto_request and not  task.task_type.froce_assign_request ) :
                            task_type_auto_request=task.task_type.auto_requests.all()
                            if(task_type_auto_request.count()>0 ):
                                task.assign_status = 3
                                task.user_assignee=None
                                task.group_assignee=None
                            else:
                                context["Error"] = " این نوع کار در ثبت درخواست خودکار دچار مشکل است با مدیر سامانه تماس بگیرید"
                                _hasError = True

                        if (not _hasError and task.task_type and task.task_type.auto_request and task.task_type.froce_assign_request) :
                            task_type_auto_request=task.task_type.auto_requests.all().first()
                            if(task_type_auto_request and task_type_auto_request.request_target):
                                task.assign_status = 4
                                task.user_assignee=task_type_auto_request.request_target
                                task.group_assignee=None
                                
                            else:
                                context["Error"] = " این نوع کار در ثبت درخواست خودکار دچار مشکل است با مدیر سامانه تماس بگیرید"
                                _hasError = True
                if not _hasError:
                    if "task_add_current" in request.POST :
                            task.current=True
                    else:
                        task.current=False
                        if "enddate" in request.POST and request.POST["enddate"]:
                            task.enddate = ConvertToMiladi(request.POST["enddate"])
                        else:
                            context["Error"] = "تاریخ پایان باید مقدار دهی شود"
                            _hasError = True
                            
                        if  "startdate" in request.POST and request.POST["startdate"]:
                            task.startdate = ConvertToMiladi(request.POST["startdate"])
                        else:
                            context["Error"] = "تاریخ شروع باید مقدار دهی شود"
                            _hasError = True
                            
                        
                if not _hasError:
                    task.description = request.POST["description"]
                    if request.POST["budget"]:
                        task.budget = int(
                            str(request.POST["budget"]).replace(",", ""))
                    else:
                        task.budget = 0
                    

                    if "progress_autocomplete" in request.POST:
                        task.progress_autocomplete = True
                    else:
                        task.progress_autocomplete = False

                    if "investigative" in request.POST:
                        task.investigative = True
                    else:
                        task.investigative = False

                    if "educational" in request.POST:
                        task.educational = True
                    else:
                        task.educational = False

                    if int(request.POST["task_portion_in_parentInputId"]) > 1 and int(request.POST["task_portion_in_parentInputId"]) <= 10 :
                        task.task_portion_in_parent = int(request.POST["task_portion_in_parentInputId"])
                    else:
                        task.task_portion_in_parent = 1

                    if int(request.POST["task_priorityInputId"]) > 0:
                        task.task_priority = int(request.POST["task_priorityInputId"])

                    if int(request.POST["task_parent"]) > 0:
                        task.task_parent = Task.objects.get(
                            pk=request.POST["task_parent"])

                    if as_user.id  in request.user.employee.GetAllChildrenUserId or as_user == request.user or (request.user.locumtenens_organization_groups.first().locumtenens_active and request.user.locumtenens_organization_groups.first().manager.id == as_user.id):
                        task.creator = as_user
                    else:
                        context["Error"] = "ایجاد کننده انتخابی مجاز نمی باشد"
                        _hasError = True
                    
                    if("prerequisite_type" in request.POST and request.POST["prerequisite_type"]!="" and int(request.POST["prerequisite_type"])>0):
                        task.prerequisite_type=int(request.POST["prerequisite_type"])
                    else:
                        task.prerequisite_type=None
                
                if not _hasError:
                    if task.enddate and task.startdate and task.task_parent:
                        valid_start_date=None
                        valid_end_date=None
                        min_solar=None
                        max_solar=None
                        temp_parent_task=task.task_parent
                        while(temp_parent_task):
                            if temp_parent_task.startdate and (valid_start_date is None or ( valid_start_date is not None and temp_parent_task.startdate > valid_start_date )):
                                valid_start_date=temp_parent_task.startdate 
                                min_solar=temp_parent_task.PersianStartDate
                            
                            if temp_parent_task.enddate and (valid_end_date is None or ( valid_end_date is not None and temp_parent_task.enddate < valid_end_date) ):
                                valid_end_date=temp_parent_task.enddate 
                                max_solar=temp_parent_task.PersianEndDate

                            if temp_parent_task.task_parent:
                                temp_parent_task=temp_parent_task.task_parent
                            else:
                                temp_parent_task=None
                        if valid_start_date and valid_end_date and ((datetime.date(*(int(s) for s in task.startdate.split('-'))) < valid_start_date  ) or (datetime.date(*(int(s) for s in task.enddate.split('-')))> valid_end_date )):
                            context["Error"] = "محدوده تاریخ انتخابی مجاز نمی باشد" +"\r\n" +":محدوده مجاز "+ min_solar +" تا "+max_solar
                            _hasError = True

                if not _hasError:
                    if int(request.POST["assign_status"]) == 1:
                        task.user_assignee = User.objects.get(
                            pk=int(request.POST["assign_key"]))
                        task.assign_status = 1
                        task.group_assignee=None
                        
                        for _request in task.task_assign_requests.all():
                            _request.delete()

                    elif int(request.POST["assign_status"]) == 2:
                        task.group_assignee = Task_Group.objects.get(
                            pk=int(request.POST["assign_key"]))
                        task.assign_status = 2
                        task.user_assignee=None
                        for _request in task.task_assign_requests.all():
                            _request.delete()
                    elif int(request.POST["assign_status"]) == 3:
                        task.assign_status = 3
                        task.user_assignee=None
                        task.group_assignee=None
                    
                    
                    task.save()

                    if (not _hasError and task.task_type and task.task_type.needs_verfication) :
                        task_type_verification=Task_Type_Verification.objects.filter(task_type=task.task_type).order_by('order')
                        for v in task_type_verification:
                            task_verification_log=Task_Verification_Log()
                            task_verification_log.verification=v
                            task_verification_log.task=task
                            if v.verification_type == 1:
                                task_verification_log.verifier=request.user.employee.organization_group.manager
                                if v.verify_by_locumtenens:
                                    task_verification_log.verifier_locumtenens=request.user.employee.organization_group.locumtenens
                            
                            elif v.verification_type == 2:
                                organization_group=Organization_Group.objects.filter(group_parent=None).first()
                                if organization_group and organization_group.manager:
                                    task_verification_log.verifier=organization_group.manager
                                    if v.verify_by_locumtenens:
                                        task_verification_log.verifier_locumtenens=organization_group.locumtenens
                                
                            elif v.verification_type == 3:
                                task_verification_log.verifier=v.verification_user

                            if task_verification_log.verifier == task.creator:
                                task_verification_log.verified = True
                                task_verification_log.last_verifier = task.creator

                            
                            task_verification_log.save()

                        

                    if (not _hasError and task.task_type and task.task_type.auto_request and not  task.task_type.froce_assign_request and task.assign_status == 3 ) or (not _hasError and task.task_type and task.task_type.needs_verfication and task_type_auto_request.count()>0) :
                        for r in task_type_auto_request:
                            try:
                                _request = Task_Assign_Request.objects.get(task=task,user=r.request_target)
                                _request.delete()
                            except Task_Assign_Request.DoesNotExist:
                                pass
                                
                            _request = Task_Assign_Request()
                            _request.task = task
                            _request.user = r.request_target
                            if (task.task_type.needs_verfication):
                                if task.task_verifications.all().exclude(verified=True).count() == 0:
                                    _request.need_verification=False
                                else:
                                    _request.need_verification=True
                            else:
                                _request.need_verification=False
                            _request.save()

                    if (task.task_type and task.task_type and task.task_type.froce_assign_request and task.assign_status==4 and task.user_assignee):
                        try:
                            _request = Task_Assign_Request.objects.get(task=task,user=task_type_auto_request.request_target)
                            _request.delete()
                        except Task_Assign_Request.DoesNotExist:
                            _request=Task_Assign_Request()
                        
                        _request.task = task
                        _request.user = task_type_auto_request.request_target
                        _request.notification_status = 2
                        _request.status = 1
                        
                        _request.save()

                    if int(request.POST["assign_status"]) == 1 and "startdate" in request.POST and request.POST["startdate"]:
                        notification=Notification()
                        notification.title="کار :"+task.name
                        notification.user=task.user_assignee
                        notification.displaytime=task.startdate
                        notification.messages="این کار در تاریخ "+request.POST["startdate"]+" شروع شده است"
                        notification.link="/task/"+str(task.pk)+"/profile/"
                        notification.save()
                        task.startdate_notification=notification
                        task.save()

                    if int(request.POST["assign_status"]) == 1 and "enddate" in request.POST and request.POST["enddate"]:
                        notification=Notification()
                        notification.title="کار :"+task.name
                        notification.user=task.user_assignee
                        notification.displaytime=task.enddate
                        notification.messages="این کار در تاریخ  "+request.POST["enddate"]+" به پایان رسیده است"
                        notification.link="/task/"+str(task.pk)+"/profile/"
                        notification.save()
                        task.enddate_notification=notification
                        task.save()

                    try:
                        if not int(request.POST['as_user']) == request.user.id:
                            notification=Notification()
                            notification.title="کار :"+task.name
                            notification.user=task.creator
                            notification.displaytime=datetime.datetime.now()
                            notification.messages="کاربر   "+request.user.get_full_name() +" این کار را به جای شما تعریف کرده است"
                            notification.link="/task/"+str(task.pk)+"/profile/"
                            notification.save()
                    except:
                        pass

                    if int(request.POST["assign_status"]) == 3:
                        saved_user_requests=[r.user.id  for r in task.task_assign_requests.all()]
                        task.assign_status = 3
                        _keys = request.POST["assign_key"].split(",")
                        for row in saved_user_requests:
                            if str(row) not in _keys:
                                _request = Task_Assign_Request.objects.get(task=task,user__id=row)
                                _request.delete()
                        for key in _keys:
                            if (int(key) not in saved_user_requests):
                                _request = Task_Assign_Request()
                                _request.task = task
                                _request.user = User.objects.get(pk=int(key))
                                if (task.task_type and task.task_type.needs_verfication):
                                    if task.task_verifications.all().exclude(verified=True).count() == 0:
                                        _request.need_verification=False
                                    else:
                                        _request.need_verification=True
                                else:
                                    _request.need_verification=False
                                _request.save()
                    if len(request.POST["prerequisite_key"]):
                        _keys = request.POST["prerequisite_key"].split(",")
                        for key in _keys:
                            _prerequisite = Task_Prerequisite()
                            _prerequisite.task = task
                            _prerequisite.prerequisite = Task.objects.get(pk=int(key))
                            _prerequisite.save()
                    if not _hasError and int(request.POST["task_type"]) > 0:
                        _all_property_of_task_type=Task_Type_Property.objects.filter(task_type__id=int(request.POST["task_type"]))
                        if (len(_all_property_of_task_type)>0):
                            for p in _all_property_of_task_type:
                                _property_name="property_"+str(p.id)
                                if p.value_type==1 and _property_name in request.POST and len(request.POST[_property_name].strip())>0:    # 1 = Task_Property_Num
                                    _task_property_num=Task_Property_Num()
                                    _task_property_num.task=task
                                    _task_property_num.task_type_property=p
                                    _task_property_num.value=decimal.Decimal(request.POST[_property_name])
                                    _task_property_num.save()
                                if p.value_type==2 and _property_name in request.POST:    # 2 = Task_Property_Text
                                    _task_property_text=Task_Property_Text()
                                    _task_property_text.task=task
                                    _task_property_text.task_type_property=p
                                    _task_property_text.value=request.POST[_property_name]
                                    _task_property_text.save()
                                if p.value_type==3 and _property_name in request.POST:    # 3 = Task_Property_date
                                    _task_property_date=Task_Property_Date()
                                    _task_property_date.task=task
                                    _task_property_date.task_type_property=p
                                    _task_property_date.value=ConvertToMiladi(request.POST[_property_name])
                                    _task_property_date.save()
                                if p.value_type==4 and _property_name in request.FILES:    # 4 = Task_Property_File
                                    _task_property_file=Task_Property_File()
                                    _task_property_file.task=task
                                    _task_property_file.task_type_property=p
                                    _task_property_file.value=request.FILES[_property_name]
                                    _task_property_file.filename=request.FILES[_property_name].name
                                    _task_property_file.save()
                                if p.value_type==5 and _property_name in request.POST and request.POST[_property_name]=="on":    # 4 = Task_Property_Bool
                                    _task_property_bool=Task_Property_Bool()
                                    _task_property_bool.task=task
                                    _task_property_bool.task_type_property=p
                                    _task_property_bool.value=True
                                    _task_property_bool.save()

                    context["Message"] = "ذخیره شد"
                    return redirect("tasks:task_list")
        except Exception as ex:
            context["Error"] = ex.args[0]

    try:
        try:
            if len(request.user.locumtenens_organization_groups.all())>0 and request.user.locumtenens_organization_groups.first().locumtenens_active:
                as_user = User.objects.get(pk=int(request.GET['as_user'])) if (request.GET['as_user'] and (int(request.GET['as_user']) > 0) and User.objects.get(pk=int(request.GET['as_user'])) and (request.user.locumtenens_organization_groups.first().manager.id in User.objects.get(pk=int(request.GET['as_user'])).employee.GetEmployeeParentSet)) else request.user
            else:
                as_user = User.objects.get(pk=int(request.GET['as_user'])) if (request.GET['as_user'] and (int(request.GET['as_user']) > 0) and User.objects.get(pk=int(request.GET['as_user'])) and (request.user.id in User.objects.get(pk=int(request.GET['as_user'])).employee.GetEmployeeParentSet)) else request.user
        except:
            as_user = request.user

        context['as_user'] = as_user
        context['task_level_list'] = Task_Level.objects.all()
        context['task_type_list'] = Task_Type.objects.all()
        tasks = Task.objects.filter(
            Q(user_assignee=as_user)| Q(group_assignee__head=as_user)| Q(public = True)).exclude(cancelled=True).exclude(confirmed=True)
        context['task_Parent_list'] = tasks
        try:
            context["children_user"]=User.objects.filter(is_active=True).filter(Q(pk__in=as_user.employee.GetDirectChildrenUserId)|Q(pk=as_user.id)).exclude(username='admin').order_by('last_name')
            if len(request.user.locumtenens_organization_groups.all())>0 and request.user.locumtenens_organization_groups.first().locumtenens_active:
                context["all_children_user"]=User.objects.filter(is_active=True).filter(Q(pk__in=request.user.locumtenens_organization_groups.first().manager.employee.GetAllChildrenUserId)|Q(pk=request.user.locumtenens_organization_groups.first().manager.id)).exclude(username='admin').order_by('last_name')
            else:
                context["all_children_user"]=User.objects.filter(is_active=True).filter(Q(pk__in=request.user.employee.GetAllChildrenUserId)|Q(pk=request.user.id)).exclude(username='admin').order_by('last_name')
        except:
            pass
        context["users"] = User.objects.filter(is_active=True).exclude(username='admin').order_by('last_name')
        context["task_groups"] = Task_Group.objects.filter(creator=as_user)
        _tree = ""
        children_set=set()
        for t in tasks:
            if t.task_parent is None or (t.task_parent not in tasks and t.task_parent is not None):
                _tree += "<ul class='myUL'>"
                _tree += getchildren(t.pk,tasks)
                _tree += " </ul>"
                children_set.add(t.pk)

        context["tree"] = _tree
    except Exception as ex:
        context["Error"] = ex.args[0]
    return render(request, 'Task/add.html', {'context': context})

def treelistchild(id,tasks_id , task_order , show_cancelled ,show_confirmed , show_last_confirm ):
    task = Task.objects.get(pk=id)
    tasks = Task.objects.filter(task_parent_id=id,pk__in=tasks_id)
    last_date_for_confirm = datetime.datetime.now() - datetime.timedelta(days=14)

    if show_cancelled == 0:
        tasks = tasks.exclude(cancelled=True)

    if show_confirmed == 0:
        if show_last_confirm == 0:
            tasks = tasks.exclude(confirmed=True)
        elif show_last_confirm == 1:
            tasks = tasks.exclude(confirmed_date__lte = last_date_for_confirm)  
        else:   
            show_last_confirm = 1
    else:
        show_confirmed = 1
    if task_order == 0:
        tasks = tasks.order_by("-created")
    if task_order == 1:
        tasks = tasks.order_by("created")
    elif task_order == 2: 
        tasks = tasks.order_by("name")
    elif task_order == 3: 
        tasks = tasks.order_by("-task_priority")
    elif task_order == 4: 
        tasks = tasks.order_by("enddate")
    else:
        task_order = 0


    if(len(tasks) > 0):
        s = "<li class='nodes' ><div id='task_tree_id_"+str(task.pk)+"' name='task_tree_node' onclick='show_task_detail("+str(task.pk)+"); show_task_attachment("+str(task.pk)+");' class='border task_tree_node'"
        if(task.cancelled):
            s+=" style='opacity:0.5;'"
        s+=" ondblclick='changevisible("+str(task.pk)+")'><div  class='rotated-arrow-icon arrow-icon' onclick='changevisible("+str(task.pk)+")' id='arrow_"+str(task.pk)+"' ></div><div class='tree_name_link' ><b>"+str(task.name).replace("<","&lt;").replace(">","&gt;")+"</b></div>"
    else:
        s = "<li class='nodes '><div id='task_tree_id_"+str(task.pk)+"' name='task_tree_node' onclick='show_task_detail("+str(task.pk)+"); show_task_attachment("+str(task.pk)+");'"
        if(task.cancelled):
            s+=" style='opacity:0.5;'"
        s+=" class='border task_tree_node'><div class='tree_name_link'><b>"+str(task.name).replace("<","&lt;").replace(">","&gt;")+"</b></div>  "
    if (task.confirmed):
        s += "<div><img class='task_confirmed_tik' src='/static/img/icon/confirm.png'>"
    else:
        s+="<div id='task_tree_progress_div'>"
        if task.current:
            s += "<div class='tree-progress task_tree_progress_bar'>"
        else:
            s += "<div class='progress tree-progress task_tree_progress_bar' style='background-color:"+str(task.ProgressColor)+"0.2)'>"
            s += "<div class='progress-bar' role='progressbar' aria-valuenow='40' aria-valuemin='0' aria-valuemax='100' style='background-color:"+str(task.ProgressColor)+"1);width:" +str(task.progress)+"%'></div>"
            s +="</div>"
            s += "<div id='task_tree_progress_percent'>" + str(task.progress) + " % </div>"
        s +="</div>"
    s += "</div></div>"

    if len(tasks) > 0:
        s += "<ul class='deactive nodes_"+str(task.pk)+"' >"
        for ch in tasks:
            # _children = Task.objects.filter(task_parent_id=ch.id)
            s += treelistchild(ch.pk,tasks_id, task_order , show_cancelled ,show_confirmed , show_last_confirm)
        s += "</ul>"

    s += "</li>"
    return (s)

# redirect when user is not logged in
@login_required(login_url='user:login')
def List(request):
    request.session["activated_menu"]="tasks"
    context = {}
    context["currentUserIsManager"]=False
    context['user_filters_selected']=request.user.pk

    as_user = request.user

    try:
        show_manager_task = int(request.GET.get("show_manager_task",""))
        context["task_list_manager_task_filter_checkbox"] = show_manager_task
        if show_manager_task and len(request.user.locumtenens_organization_groups.all())>0 and \
            request.user.locumtenens_organization_groups.first().locumtenens_active:
            as_user = request.user.locumtenens_organization_groups.first().manager
    except:
        show_manager_task = 0
        context["task_list_manager_task_filter_checkbox"] = show_manager_task
    tasks=None
    if(request.user.employee.organization_group.manager==request.user):
        context["currentUserIsManager"]=True
        try:
            context["children_current_user"]=User.objects.filter(is_active=True).filter(Q(pk__in=request.user.employee.GetAllChildrenUserId)|Q(pk=request.user.id)).order_by('last_name')
        except:
            pass
        try:
            userSelected = int(request.GET.get("uid","0"))
            try:
                if show_manager_task == 0:
                    as_user = User.objects.get(pk=int(userSelected))
            except:
                if show_manager_task == 0:
                    as_user = request.user
            if userSelected in request.user.employee.GetAllChildrenUserId:
                context["user_filters_selected"] = userSelected
            else:
                context["user_filters_selected"] = request.user.pk
        except:
            context["user_filters_selected"] = request.user.pk
        tasks = Task.objects.filter( \
            Q(creator=as_user) | Q(user_assignee=as_user)|Q(creator__pk__in=as_user.employee.GetAllChildrenUserId)|Q(user_assignee__pk__in=as_user.employee.GetAllChildrenUserId)|\
                Q(group_assignee__head=as_user)|Q(pk__in=as_user.employee.UnderTaskGroupTasks)|Q(pk__in=as_user.employee.CopyFromAccessTasks)).exclude(assign_status=4,user_assignee=as_user)\
                    .annotate(Count('children', distinct=True))
    else:
        tasks = Task.objects.filter( \
            Q(creator=as_user) | Q(user_assignee=as_user)|Q(creator__pk__in=as_user.employee.GetAllChildrenUserId)|Q(user_assignee__pk__in=as_user.employee.GetAllChildrenUserId)|\
                Q(group_assignee__head=request.user)|Q(pk__in=request.user.employee.UnderTaskGroupTasks)|Q(pk__in=as_user.employee.CopyFromAccessTasks)).exclude(assign_status=4,user_assignee=as_user)\
                    .annotate(Count('children', distinct=True))
    
    # Q(user_assignee__in=Subquery(Tasks.objects.filter()))
    task_requests=Task.objects.filter(assign_status=4,user_assignee=as_user).annotate(Count('children', distinct=True))
    try:
        task_order = int(request.GET.get("task_order",""))
        context["task_list_sort_method"] = task_order
    except:
        task_order=0
        context["task_list_sort_method"] = task_order
        
    try:
        show_cancelled = int(request.GET.get("show_cancelled",""))
        context["task_list_cancelled_filter_checkbox"] = show_cancelled
    except:
        show_cancelled = 0
        context["task_list_cancelled_filter_checkbox"] = show_cancelled

    try:
        show_confirmed = int(request.GET.get("show_confirmed",""))
        context["task_list_confirmed_filter_checkbox"] =show_confirmed
    except:
        show_confirmed = 0
        context["task_list_confirmed_filter_checkbox"] =show_confirmed
    
    try:
        show_last_confirm = int(request.GET.get("show_last_confirm",""))
        context["task_list_last_confirmed_filter_checkbox"] = show_last_confirm
    except:
        show_last_confirm = 1
        context["task_list_last_confirmed_filter_checkbox"] = show_last_confirm



    last_date_for_confirm = datetime.datetime.now() - datetime.timedelta(days=14)

    if show_cancelled == 0:
        tasks = tasks.exclude(cancelled=True)
        task_requests=task_requests.exclude(cancelled=True)
    else:
        show_cancelled =1 
        context["task_list_cancelled_filter_checkbox"] = show_cancelled

    if show_confirmed == 0:
        if show_last_confirm == 0:
            tasks = tasks.exclude(confirmed=True)
            task_requests=task_requests.exclude(confirmed=True)
        elif show_last_confirm == 1:
            tasks = tasks.exclude(confirmed=True,confirmed_date__lte = last_date_for_confirm)  
            task_requests=task_requests.exclude(confirmed=True,confirmed_date__lte = last_date_for_confirm)  
        else:   
            show_last_confirm = 1
            context["task_list_last_confirmed_filter_checkbox"] = show_last_confirm
    else:
        show_confirmed = 1
        context["task_list_confirmed_filter_checkbox"] =show_confirmed
    if task_order == 0:
        tasks = tasks.order_by("-created")
        task_requests = task_requests.order_by("-created")
    if task_order == 1:
        tasks = tasks.order_by("created")
        task_requests = task_requests.order_by("created")
    elif task_order == 2: 
        tasks = tasks.order_by("name")
        task_requests=task_requests.order_by("name")
    elif task_order == 3: 
        tasks = tasks.order_by("-task_priority")
        task_requests=task_requests.order_by("-task_priority")
    elif task_order == 4: 
        tasks = tasks.order_by("enddate")
        task_requests=task_requests.order_by("enddate")
    else:
        task_order = 0
        context["task_list_sort_method"] = task_order


    #show all parent of tasks 
    if request.user==request.user.employee.organization_group.manager or (request.user==request.user.employee.organization_group.locumtenens\
        and request.user.employee.organization_group.locumtenens_active):
        parent_tasks = tasks.exclude(task_parent__pk__in=tasks.values_list('pk',flat=True))
        for t in parent_tasks:
            if (t.task_parent not in parent_tasks and t.task_parent is not None  and t.user_assignee==request.user and not t.creator == request.user):
                task_parent=t.task_parent
                while (task_parent is not None):
                    t_parent=Task.objects.filter(pk=task_parent.id)  
                    tasks |=t_parent    #append to queryset
                    task_parent=t_parent.first().task_parent

    tasks_id =tasks.values_list('pk',flat=True)
    
    parent_tasks = tasks.exclude(task_parent__pk__in=tasks_id)

    _tree = ""
    try:

        for task_node in parent_tasks :

            s = "<ul class='tree'><li class='nodes' ><div id='task_tree_id_"+str(task_node.pk)+"' name='task_tree_node' class='border task_tree_node' onclick='show_task_detail("+str(task_node.pk)+"); show_task_attachment("+str(task_node.pk)+");'"
            if task_node.cancelled :
                s+=" style='opacity:0.5;'"
            if task_node.children__count:
                s+=" ondblclick='changevisible("+str(task_node.pk)+")'><div  class='rotated-arrow-icon arrow-icon' onclick='changevisible("+str(task_node.pk)+")' id='arrow_"+str(task_node.pk)+"' ></div"
            s+="><div class='tree_name_link' ><b>"+str(task_node.name).replace("<","&lt;").replace(">","&gt;")+"</b>"
            if request.user.employee.in_staff_group and (not task_node.current) and task_node.startdate and task_node.enddate:
                s+="<a href='/task/" + str(task_node.pk) + "/gantt/' class='task_tree_gantt_icon'></a>"
            s+="</div>"
            if task_node.confirmed:
                s += "<div><img class='task_confirmed_tik' src='/static/img/icon/confirm.png'>"
            else:
                s+="<div id='task_tree_progress_div'>"
                if task_node.current:
                    s += "<div class='tree-progress task_tree_progress_bar'></div>"
                else:
                    s += "<div class='progress tree-progress task_tree_progress_bar' style='background-color:"+str(task_node.ProgressColor)+"0.2)'>"
                    s += "<div class='progress-bar' role='progressbar' aria-valuenow='40' aria-valuemin='0' aria-valuemax='100' style='background-color:"+str(task_node.ProgressColor)+"1);width:" +str(task_node.progress)+"%'></div>"
                    s +="</div>"
                    s += "<div id='task_tree_progress_percent'>" + str(task_node.progress) + " % </div>"
                
            s += "</div></div>"

            if task_node.children__count:
                s += "<ul class='deactive nodes_"+str(task_node.pk)+"' ><!--"+str(task_node.pk)+"--></ul>"
                
            s += "</li></ul>"

            _tree += s

        while True:
            parent_tasks = tasks.filter(task_parent__pk__in=parent_tasks.values_list('pk',flat=True))
            if len(parent_tasks) == 0:
                break
            else:
                for task_node in parent_tasks :
                    s = "<li class='nodes' ><div id='task_tree_id_"+str(task_node.pk)+"' name='task_tree_node' class='border task_tree_node' onclick='show_task_detail("+str(task_node.pk)+"); show_task_attachment("+str(task_node.pk)+");'"
                    if task_node.cancelled :
                        s+=" style='opacity:0.5;'"
                    if task_node.children__count:
                        s+=" ondblclick='changevisible("+str(task_node.pk)+")'><div  class='rotated-arrow-icon arrow-icon' onclick='changevisible("+str(task_node.pk)+")' id='arrow_"+str(task_node.pk)+"' ></div"
                    s+="><div class='tree_name_link' ><b>"+str(task_node.name).replace("<","&lt;").replace(">","&gt;")+"</b>"
                    if request.user.employee.in_staff_group and (not task_node.current) and task_node.startdate and task_node.enddate:
                        s+="<a href='/task/" + str(task_node.pk) + "/gantt/' class='task_tree_gantt_icon'></a>"
                    s+="</div>"
                    if task_node.confirmed:
                        s += "<div><img class='task_confirmed_tik' src='/static/img/icon/confirm.png'>"
                    else:
                        s+="<div id='task_tree_progress_div'>"
                        if task_node.current:
                            s += "<div class='tree-progress task_tree_progress_bar'></div>"
                        else:
                            s += "<div class='progress tree-progress task_tree_progress_bar' style='background-color:"+str(task_node.ProgressColor)+"0.2)'>"
                            s += "<div class='progress-bar' role='progressbar' aria-valuenow='40' aria-valuemin='0' aria-valuemax='100' style='background-color:"+str(task_node.ProgressColor)+"1);width:" +str(task_node.progress)+"%'></div>"
                            s +="</div>"
                            s += "<div id='task_tree_progress_percent'>" + str(task_node.progress) + " % </div>"
                        
                    s += "</div></div>"

                    if task_node.children__count:
                        s += "<ul class='deactive nodes_"+str(task_node.pk)+"' ><!--"+str(task_node.pk)+"--></ul>"
                        
                    s += "</li><!--"+str(task_node.task_parent.pk)+"-->"

                    
                    _tree = _tree.replace("<!--"+str(task_node.task_parent.pk)+"-->" ,s)

    except:
        pass

 
    tasks_id |= task_requests.values_list('pk',flat=True)
    context["tasks_id"]=tasks_id
    if len(task_requests)>0:
        _tree += "<ul class='tree'>"
        _tree += "<li class='nodes '><div id='task_tree_id_-1'  ondblclick='changevisible(-1)' style='background-color: lightcyan;' name='task_tree_node'"
        _tree +=" class='border task_tree_node'><div  class='rotated-arrow-icon arrow-icon' onclick='changevisible(-1)' id='arrow_-1' ></div><div class='tree_name_link'><b>درخواست ها </b></div> "
        _tree += "</div></div>"
        for t in task_requests:
            if t.task_parent is None or (t.task_parent not in task_requests and t.task_parent is not None ):
                _tree+= "<ul class='deactive nodes_-1' >"
                _tree += treelistchild(t.pk,tasks_id, task_order , show_cancelled ,show_confirmed , show_last_confirm )
                _tree += "</ul>"
        _tree +="</li>"
        _tree += " </ul>"

    tasks_id = list(tasks_id)
    tasks_id.append(-1)
    context["tasks_id"]=tasks_id


    
    context["tree"] = _tree
    context["isLocuntenens"]=False

    if(len(request.user.locumtenens_organization_groups.all())>0):
        context["isLocuntenens"]=True
    
    return render(request, 'task/List.html', {'context': context})

# redirect when user is not logged in
@login_required(login_url='user:login')
def Edit(request, id):
    request.session["activated_menu"]="tasks"
    context = {}
    if len(request.user.locumtenens_organization_groups.all())>0 and request.user.locumtenens_organization_groups.first().locumtenens_active:
        as_user = request.user.locumtenens_organization_groups.first().manager
    else:
        as_user = request.user
    _user = request.user
    # task=Task.objects.get(pk=id)
    
    task = Task.objects.filter(pk=id).filter( \
        Q(creator=as_user) | Q(user_assignee=as_user)|Q(creator__pk__in=as_user.employee.GetAllChildrenUserId)|Q(user_assignee__pk__in=as_user.employee.GetAllChildrenUserId)|\
            Q(group_assignee__head=request.user)|Q(pk__in=request.user.employee.UnderTaskGroupTasks)|Q(pk__in=as_user.employee.CopyFromAccessTasks))

    if len(task)==0 :
        # if (request.user in [u.request_target for u in Task_Type_Auto_Request.objects.filter(task_type__in=Task.objects.filter(pk=id).values('task_type'))]):
        if Task_Assign_Request.objects.filter(task__pk= id, status=None,notification_status=None,user=request.user).exclude(need_verification=True):
            task = Task.objects.get(pk=id)
        else:
            raise(PermissionDenied)
    else:
        task=task[0]
        
    if request.method == "POST":
        try:
            task = Task.objects.get(pk=id)
            
            with transaction.atomic():
                _hasError = False
                
                if "task_edit_confirmed" in request.POST and request.POST["task_edit_confirmed"]=="on" and ( task.progress == 100 ):
                    if (task.user_assignee and task.user_assignee.employee.GetEmployeeParent == _user.id ) or (task.group_assignee and task.group_assignee.head.employee.GetEmployeeParent == _user.id ):
                        task.confirmed=True
                        task.confirmed_date=datetime.datetime.now()
                        if "ScoreInputId" in request.POST and int(request.POST["ScoreInputId"]) >= 0:
                            task.score = int(request.POST["ScoreInputId"])
                            
                        task.save()
                        ############################## notification

                        if task.startdate_notification:
                            try:
                                notification=Notification.objects.get(pk=task.startdate_notification.pk)
                                notification.closed = True
                                notification.save()
                            except:
                                pass

                        if task.enddate_notification:
                            try:
                                notification=Notification.objects.get(pk=task.enddate_notification.pk)
                                notification.closed = True
                                notification.save()
                            except:
                                pass
                        ############################## notification
                        for t in task.GetAllTaskChildrenId:
                            _task=Task.objects.get(pk=t)
                            if not _task.cancelled:
                                _task.progress = 100
                                _task.confirmed = True
                                _task.confirmed_date = datetime.datetime.now()
                                _task.save()
                        if (not request.POST["previous_page"]==""):
                            return HttpResponseRedirect(request.META.get('HTTP_REEFER',request.POST["previous_page"]))
                        else:
                            return redirect("tasks:task_profile", task.id )

                    else:
                        raise PermissionDenied
                
                if task.creator == as_user or as_user.id in task.creator.employee.GetEmployeeParentSet :
                    old_task_mod_time = task.updated

                    if "task_edit_cancelled" in request.POST and request.POST["task_edit_cancelled"]=="on":
                        task.cancelled=True
                        task.save()
                        ############################## notification

                        if task.startdate_notification:
                            try:
                                notification=Notification.objects.get(pk=task.startdate_notification.pk)
                                notification.closed = True
                                notification.save()
                            except:
                                pass

                        if task.enddate_notification:
                            try:
                                notification=Notification.objects.get(pk=task.enddate_notification.pk)
                                notification.closed = True
                                notification.save()
                            except:
                                pass
                        ############################## notification
                        for t in task.GetAllTaskChildrenId:
                            _task=Task.objects.get(pk=t)
                            _task.cancelled=True
                            _task.save()
                        
                        if (not request.POST["previous_page"]==""):
                            return HttpResponseRedirect(request.META.get('HTTP_REEFER',request.POST["previous_page"]))
                        else:
                            return redirect("tasks:task_profile",task.id )



                    if request.POST["name"]:
                        task.name = request.POST["name"]
                    else:
                        _hasError = True
                        context["Error"] = "فیلد عنوان کار باید مقدار دهی شود"

                    if task.task_type != None and "task_type" in request.POST  and int(request.POST["task_type"]) != task.task_type.id:
                        context["Error"] = "تغییر نوع کار مجاز نمی باشد"
                        _hasError = True

                    if len(task.task_assign_requests.all().exclude(need_verification=True)) > 0 and task.user_assignee and len(task.task_verifications.all())>0:
                        context["Error"] = "ویرایش درخواست پذیرفته شده یا بررسی شده مجاز نمی باشد"
                        _hasError = True

                    if not _hasError and "task_parent" in request.POST:
                        if int(request.POST["task_parent"]) > 0:
                            _tasks = Task.objects.filter(
                                name=request.POST["name"], task_parent_id=0).exclude(pk=id)
                        else:
                            _tasks = Task.objects.filter(
                                name=request.POST["name"], task_parent_id=None).exclude(pk=id)
                        if (len(_tasks) > 0):
                            context["Error"] = "فیلدهای عنوان کار و والد باید یکتا باشند"
                            _hasError = True
                    if not _hasError and "task_level" in request.POST:
                        if int(request.POST["task_level"]) > 0:
                            task.task_level = Task_Level.objects.get(
                                pk=request.POST["task_level"])
                        else:
                            context["Error"] = "فیلد سطح کار باید مقدار دهی شود"
                            _hasError = True
                    
                    if not _hasError and int(request.POST["task_parent"]) > 0 and "task_parent" in request.POST and request.POST["task_parent"]!=id and request.POST['task_parent'] not in task.GetAllTaskChildrenId:
                        if (int(request.POST["task_parent"]) in Task.objects.get(pk=id).GetTaskChildrenId) or id == int(request.POST["task_parent"]):
                            context["Error"] = "والد انتخاب شده مجاز نمی باشد"
                            _hasError = True
                        else:
                            task.task_parent = Task.objects.get(
                                pk=request.POST["task_parent"])
                    else:
                        if not _hasError and  as_user.employee.GetEmployeeParent:
                            context["Error"] = "فیلد والد باید مقدار دهی شود"
                            _hasError = True
                        else:
                            task.task_parent = None
                            task.prerequisite_type=None

                    
                    if not _hasError and len(task.GetTaskChildrenId)>0 :
                        if (task.assign_status !=  int(request.POST["assign_status"])) and not (task.assign_status == None and request.POST["assign_status"] == '0'):
                            context["Error"] = "اجازه تغییر مسئول برای کاری که زیر مجموعه دارد، وجود ندارد"
                            _hasError = True
                        if (task.user_assignee and int(request.POST["assign_key"]) != task.user_assignee.id and task.assign_status == 1) or (task.group_assignee and int(request.POST["assign_key"]) != task.group_assignee.id and task.assign_status == 2):
                            context["Error"] = "اجازه تغییر مسئول برای کاری که زیر مجموعه دارد، وجود ندارد"
                            _hasError = True
                    
                    if not _hasError:
                        if int(request.POST["task_parent"]) > 0 and int(request.POST["assign_status"]) != 1  :
                            _parent = Task.objects.get(pk=request.POST["task_parent"])
                            if _parent.group_assignee or _parent.UnderTaskGroup:
                                if int(request.POST["task_type"]) > 0:
                                    task.task_type = Task_Type.objects.get(pk=request.POST["task_type"])
                                    if (not task.task_type.auto_requests.all().count()>0) :
                                        context["Error"] = "اجازه انتخاب کارگروه و یا ثبت درخواست وجود ندارد"
                                        _hasError = True
                                else:
                                    context["Error"] = "اجازه انتخاب کارگروه و یا ثبت درخواست وجود ندارد"
                                    _hasError = True
                                
                        if int(request.POST["task_parent"]) > 0 and int(request.POST["assign_status"]) == 1:
                            _parent = Task.objects.get(pk=request.POST["task_parent"])
                            if _parent.group_assignee:
                                _user_assignee = User.objects.get(pk=int(request.POST["assign_key"]))
                                
                                _members=[member.user for member in Task_Group_Member.objects.filter(group=_parent.group_assignee)]
                                if ( _user_assignee!=_parent.group_assignee.head and _user_assignee not in _members):
                                    context["Error"] = "مسئول انتخابی مجاز نمی باشد"
                                    _hasError = True

                            elif _parent.UnderTaskGroup:
                                _user_assignee = User.objects.get(pk=int(request.POST["assign_key"]))
                                _members=[member.user for member in Task_Group_Member.objects.filter(group=_parent.UnderTaskGroup)]

                                if (as_user ==_parent.UnderTaskGroup.head and _user_assignee!=_parent.UnderTaskGroup.head and _user_assignee not in _members):
                                    context["Error"] = "مسئول انتخابی مجاز نمی باشد"
                                    _hasError = True
                                elif(as_user !=_parent.UnderTaskGroup.head and _user_assignee!= as_user ):
                                    context["Error"] = "مسئول انتخابی مجاز نمی باشد"
                                    _hasError = True
                    # -------------------------------------------
                    if not _hasError:
                        if int(request.POST["assign_status"]) == 1:
                            task.user_assignee = User.objects.get(
                                pk=int(request.POST["assign_key"]))
                            task.assign_status = 1
                            task.group_assignee=None
                            
                            for _request in task.task_assign_requests.all():
                                _request.delete()
                        elif int(request.POST["assign_status"]) == 2:
                            task.group_assignee = Task_Group.objects.get(
                                pk=int(request.POST["assign_key"]))
                            task.assign_status = 2
                            task.user_assignee=None
                            for _request in task.task_assign_requests.all():
                                _request.delete()
                        elif int(request.POST["assign_status"]) == 3:
                            task.assign_status = 3
                            task.user_assignee=None
                            task.group_assignee=None
                    # -------------------------------------------
                    if not _hasError:
                        if "task_edit_current" in request.POST :
                                task.current=True
                                task.startdate =None
                                task.enddate =None
                        else:
                            task.current=False
                            if "enddate" in request.POST and request.POST["enddate"]:
                                task.enddate = ConvertToMiladi(request.POST["enddate"])
                            else:
                                context["Error"] = "تاریخ پایان باید مقدار دهی شود"
                                _hasError = True
                                
                            if  "startdate" in request.POST and request.POST["startdate"]:
                                task.startdate = ConvertToMiladi(request.POST["startdate"])
                            else:
                                context["Error"] = "تاریخ شروع باید مقدار دهی شود"
                                _hasError = True
                            
                    if not _hasError:
                        if task.enddate and task.startdate and task.task_parent:
                            valid_start_date=None
                            valid_end_date=None
                            min_solar=None
                            max_solar=None
                            temp_parent_task=task.task_parent
                            while(temp_parent_task):
                                if temp_parent_task.startdate and (valid_start_date is None or ( valid_start_date is not None and temp_parent_task.startdate > valid_start_date )):
                                    valid_start_date=temp_parent_task.startdate 
                                    min_solar=temp_parent_task.PersianStartDate
                                
                                if temp_parent_task.enddate and (valid_end_date is None or ( valid_end_date is not None and temp_parent_task.enddate < valid_end_date) ):
                                    valid_end_date=temp_parent_task.enddate 
                                    max_solar=temp_parent_task.PersianEndDate

                                if temp_parent_task.task_parent:
                                    temp_parent_task=temp_parent_task.task_parent
                                else:
                                    temp_parent_task=None
                            if valid_start_date and valid_end_date and ((datetime.date(*(int(s) for s in task.startdate.split('-'))) < valid_start_date  ) or (datetime.date(*(int(s) for s in task.enddate.split('-')))> valid_end_date )):
                                context["Error"] = "محدوده تاریخ انتخابی مجاز نمی باشد" +"\r\n" +":محدوده مجاز "+ min_solar +" تا "+max_solar
                                _hasError = True
                    task_type_changed=False
                    if not _hasError:
                        if "task_type" in request.POST and task.task_type == None:
                            if int(request.POST["task_type"]) > 0 :
                                task.task_type = Task_Type.objects.get(
                                    pk=request.POST["task_type"])
                                task_type_changed=True
                                if (task.task_type.froce_assign_request and not task.task_type.auto_request) :
                                    context["Error"] = " این نوع کار در ثبت درخواست خودکار دچار مشکل است با مدیر سامانه تماس بگیرید"
                                    _hasError = True
                        
                                if (not _hasError and task.task_type and task.task_type.needs_verfication) :
                                    task_type_verification=Task_Type_Verification.objects.filter(task_type=task.task_type).order_by('order')
                                    if task_type_verification.count()==0:
                                        context["Error"] = " این نوع کار در ثبت تائیدیه درخواست دچار مشکل است با مدیر سامانه تماس بگیرید"
                                        _hasError = True
                                    if not _hasError:
                                        request_user_key=request.POST["assign_key"].strip().split(",")
                                        task_type_auto_request=task.task_type.auto_requests.all()
                                        if (len(request_user_key)==0 and request_user_key[0].strip() == '' ) and task_type_auto_request.count()==0 :
                                            context["Error"] = "کاربر مورد درخواست نامشخص است"
                                            _hasError = True
                                else:
                                    if (not _hasError and task.task_type and task.task_type.auto_request and not  task.task_type.froce_assign_request ) :
                                        task_type_auto_request=task.task_type.auto_requests.all()
                                        if(task_type_auto_request.count()>0 ):
                                            task.assign_status = 3
                                            task.user_assignee=None
                                            task.group_assignee=None
                                        else:
                                            context["Error"] = " این نوع کار در ثبت درخواست خودکار دچار مشکل است با مدیر سامانه تماس بگیرید"
                                            _hasError = True

                                    if (not _hasError and task.task_type and task.task_type.auto_request and task.task_type.froce_assign_request) :
                                        task_type_auto_request=task.task_type.auto_requests.all().first()
                                        if(task_type_auto_request and task_type_auto_request.request_target):
                                            task.assign_status = 4
                                            task.user_assignee=task_type_auto_request.request_target
                                            task.group_assignee=None
                                            
                                        else:
                                            context["Error"] = " این نوع کار در ثبت درخواست خودکار دچار مشکل است با مدیر سامانه تماس بگیرید"
                                            _hasError = True


                        task.description = request.POST["description"]
                        if request.POST["budget"]:
                            task.budget = int(
                                str(request.POST["budget"]).replace(",", ""))
                        else:
                            task.budget = 0
                        
                        if "progress_autocomplete" in request.POST:
                            task.progress_autocomplete = True
                        else:
                            task.progress_autocomplete = False

                        if "investigative" in request.POST:
                            task.investigative = True
                        else:
                            task.investigative = False

                        if "educational" in request.POST:
                            task.educational = True
                        else:
                            task.educational = False

                        if "task_portion_in_parentInputId" in request.POST and  int(request.POST["task_portion_in_parentInputId"]) > 1 and int(request.POST["task_portion_in_parentInputId"]) <= 10:
                            task.task_portion_in_parent = int(
                                request.POST["task_portion_in_parentInputId"])
                        else:
                            task.task_portion_in_parent = 1
                        if int(request.POST["task_priorityInputId"]) > 0:
                            task.task_priority = int(request.POST["task_priorityInputId"])
                        else:
                            task.task_priority=0
                        
                        if("prerequisite_type" in request.POST and request.POST["prerequisite_type"]!="" and int(request.POST["prerequisite_type"])>0):
                            task.prerequisite_type=int(request.POST["prerequisite_type"])
                        else:
                            task.prerequisite_type=None
                        task.save()
                        if (not _hasError and task.task_type and task.task_type.needs_verfication and task_type_changed) :
                            task_type_verification=Task_Type_Verification.objects.filter(task_type=task.task_type).order_by('order')
                            for v in task_type_verification:
                                task_verification_log=Task_Verification_Log()
                                task_verification_log.verification=v
                                task_verification_log.task=task
                                if v.verification_type == 1:
                                    task_verification_log.verifier=request.user.employee.organization_group.manager
                                    if v.verify_by_locumtenens:
                                        task_verification_log.verifier_locumtenens=request.user.employee.organization_group.locumtenens
                                
                                elif v.verification_type == 2:
                                    organization_group=Organization_Group.objects.filter(group_parent=None).first()
                                    if organization_group and organization_group.manager:
                                        task_verification_log.verifier=organization_group.manager
                                        if v.verify_by_locumtenens:
                                            task_verification_log.verifier_locumtenens=organization_group.locumtenens
                                    
                                elif v.verification_type == 3:
                                    task_verification_log.verifier=v.verification_user
                                
                                task_verification_log.save()

                        if (not _hasError and task.task_type and task_type_changed and task.task_type.auto_request and not  task.task_type.froce_assign_request and task.assign_status == 3 ) or (not _hasError and  task.task_type and task_type_changed and task.task_type.needs_verfication and task_type_auto_request.count()>0) :
                            for r in task_type_auto_request:
                                try:
                                    _request = Task_Assign_Request.objects.get(task=task,user=r.request_target)
                                    _request.delete()
                                except Task_Assign_Request.DoesNotExist:
                                    pass
                                    
                                _request = Task_Assign_Request()
                                _request.task = task
                                _request.user = r.request_target
                                if (task.task_type.needs_verfication):
                                    _request.need_verification=True
                                else:
                                    _request.need_verification=False
                                _request.save()

                        if (task.task_type and task.task_type and task_type_changed and task.task_type.froce_assign_request and task.assign_status==4 and task.user_assignee):
                            try:
                                _request = Task_Assign_Request.objects.get(task=task,user=task_type_auto_request.request_target)
                                _request.delete()
                            except Task_Assign_Request.DoesNotExist:
                                _request=Task_Assign_Request()
                            
                            _request.task = task
                            _request.user = task_type_auto_request.request_target
                            _request.notification_status = 2
                            _request.status = 1
                            
                            _request.save()

                        ############################## notification

                        if int(request.POST["assign_status"]) == 1 and "startdate" in request.POST and request.POST["startdate"]:
                            try:
                                notification=Notification.objects.get(pk=task.startdate_notification.pk)
                                if notification.user!=task.user_assignee or notification.closed == False:
                                    notification.title="کار :"+task.name
                                    notification.user=task.user_assignee
                                    notification.displaytime=task.startdate
                                    notification.messages="این کار در تاریخ  "+request.POST["startdate"]+" شروع شده است"
                                    notification.link="/task/"+str(task.pk)+"/profile/"
                                    notification.save()
                            except:
                                pass

                        if int(request.POST["assign_status"]) == 1 and "enddate" in request.POST and request.POST["enddate"]:
                            try:
                                notification=Notification.objects.get(pk=task.enddate_notification.pk)
                                if notification.user!=task.user_assignee or notification.closed == False:
                                    notification.title="کار :"+task.name
                                    notification.user=task.user_assignee
                                    notification.displaytime=task.enddate
                                    notification.messages=" این کار در تاریخ"+request.POST["enddate"]+" به پایان رسیده است"
                                    notification.link="/task/"+str(task.pk)+"/profile/"
                                    notification.save()
                            except:
                                pass

                        if task.updated != old_task_mod_time and task.creator != request.user:
                            try:
                                notification = Notification()
                                notification.title="کار :"+task.name
                                notification.user=task.creator
                                notification.displaytime=datetime.datetime.now()
                                notification.messages=" این کار در تاریخ"+jdt.datetime.strftime(jdt.datetime.now(), format="%Y/%m/%d %H:%M:%S")+" توسط مدیر شما " + request.user.get_full_name() + " ویرایش شده است"
                                notification.link="/task/"+str(task.pk)+"/profile/"
                                notification.save()
                            except:
                                pass
                        ############################## notification

                        if int(request.POST["assign_status"]) == 3:
                            saved_user_requests=[r.user.id  for r in task.task_assign_requests.all()]
                            task.assign_status = 3
                            _keys = request.POST["assign_key"].split(",")
                            for row in saved_user_requests:
                                if str(row) not in _keys:
                                    _request = Task_Assign_Request.objects.get(task=task,user__id=row)
                                    _request.delete()
                            for key in _keys:
                                if (int(key) not in saved_user_requests):
                                    _request = Task_Assign_Request()
                                    _request.task = task
                                    _request.user = User.objects.get(pk=int(key))
                                    _request.save()
                        

                        _keys = request.POST["prerequisite_key"].split(",")
                        saved_prerequisite_key=[p.prerequisite.id  for p in Task_Prerequisite.objects.filter(task=task)]
                        
                        for p in saved_prerequisite_key:
                            if str(p) not in _keys:
                                    prerequisite = Task_Prerequisite.objects.get(task=task,prerequisite__id=p)
                                    prerequisite.delete()
                        for key in _keys:
                            if (key):
                                if (int(key) not in saved_prerequisite_key):
                                    try:
                                        _prerequisite = Task_Prerequisite()
                                        _prerequisite.task = task
                                        _prerequisite.prerequisite = Task.objects.get(pk=int(key))
                                        _prerequisite.save()
                                    except:
                                        pass

                        
                        _task_property_nums=Task_Property_Num.objects.filter(task=task)
                        for p in _task_property_nums:
                            p.deleted=True
                            p.save()
                        
                        _task_property_texts=Task_Property_Text.objects.filter(task=task)
                        for p in _task_property_texts:
                            p.deleted=True
                            p.save()

                        _task_property_dates=Task_Property_Date.objects.filter(task=task)
                        for p in _task_property_dates:
                            p.deleted=True
                            p.save()

                        _task_property_files=Task_Property_File.objects.filter(task=task)
                        for p in _task_property_files:
                            p.deleted=True
                            p.save()
                        
                        _task_property_bool=Task_Property_Bool.objects.filter(task=task)
                        for p in _task_property_bool:
                            p.deleted=True
                            p.save()

                        if task.task_type  and not _hasError:

                            
                            _all_property_of_task_type=Task_Type_Property.objects.filter(task_type=task.task_type)
                            if (len(_all_property_of_task_type)>0):
                                for p in _all_property_of_task_type:
                                    _property_name="property_"+str(p.id)
                                    if p.value_type==1 and _property_name in request.POST and request.POST[_property_name]!='':    # 1 = Task_Property_Num
                                        _task_property_num=None
                                        try:
                                            _task_property_num=Task_Property_Num.objects.get(task=task,task_type_property=p)
                                            try:
                                                _task_property_num.value=decimal.Decimal(request.POST[_property_name])
                                            except:
                                                _task_property_num.value=None
                                            _task_property_num.deleted=False
                                            _task_property_num.save()
                                        except Task_Property_Num.DoesNotExist:
                                            _task_property_num=None
                                        if _task_property_num is None:
                                            _task_property_num=Task_Property_Num()
                                            _task_property_num.task=task
                                            _task_property_num.task_type_property=p
                                            try:
                                                _task_property_num.value=decimal.Decimal(request.POST[_property_name])
                                            except:
                                                _task_property_num.value=None
                                            _task_property_num.save()
                                    
                                    if p.value_type==2 and _property_name in request.POST:    # 2 = Task_Property_Text
                                        _task_property_text=None
                                        try:
                                            _task_property_text=Task_Property_Text.objects.get(task=task,task_type_property=p)
                                            _task_property_text.value=request.POST[_property_name]
                                            _task_property_text.deleted=False
                                            _task_property_text.save()
                                        except Task_Property_Text.DoesNotExist:
                                            _task_property_text=None
                                        if _task_property_text is None:
                                            _task_property_text=Task_Property_Text()
                                            _task_property_text.task=task
                                            _task_property_text.task_type_property=p
                                            _task_property_text.value=request.POST[_property_name]
                                            _task_property_text.save()
                                    
                                    

                                    if p.value_type==3 and _property_name in request.POST  and request.POST[_property_name]!='':    # 3 = Task_Property_date
                                        _task_property_date=None
                                        try:
                                            _task_property_date=Task_Property_Date.objects.get(task=task,task_type_property=p)
                                            _task_property_date.value=ConvertToMiladi(request.POST[_property_name])
                                            _task_property_date.deleted=False
                                            _task_property_date.save()
                                        except Task_Property_Date.DoesNotExist:
                                            _task_property_date=None
                                        if _task_property_date is None:
                                            _task_property_date=Task_Property_Date()
                                            _task_property_date.task=task
                                            _task_property_date.task_type_property=p
                                            _task_property_date.value=ConvertToMiladi(request.POST[_property_name])
                                            _task_property_date.save()
                                    
                                    if p.value_type==4 and _property_name in request.FILES:    # 4 = Task_Property_File
                                        _task_property_file=None
                                        try:
                                            _task_property_file=Task_Property_File.objects.get(task=task,task_type_property=p)
                                            _task_property_file.value.delete()
                                            _task_property_file.value=request.FILES[_property_name]
                                            _task_property_file.filename=request.FILES[_property_name].name
                                            _task_property_file.deleted=False
                                            _task_property_file.save()
                                        except Task_Property_File.DoesNotExist:
                                            _task_property_file=None
                                        if _task_property_file is None:
                                            _task_property_file=Task_Property_File()
                                            _task_property_file.task=task
                                            _task_property_file.task_type_property=p
                                            _task_property_file.value=request.FILES[_property_name]
                                            _task_property_file.filename=request.FILES[_property_name].name
                                            _task_property_file.save()

                                    if p.value_type==5 and _property_name in request.POST and request.POST[_property_name]=="on":    # 5 = Task_Property_bool
                                        _task_property_bool=None
                                        try:
                                            _task_property_bool=Task_Property_Bool.objects.get(task=task,task_type_property=p)
                                            _task_property_bool.value=True
                                            _task_property_bool.deleted=False
                                            _task_property_bool.save()
                                        except Task_Property_Bool.DoesNotExist:
                                            _task_property_bool=None
                                        if _task_property_bool is None:
                                            _task_property_bool=Task_Property_Bool()
                                            _task_property_bool.task=task
                                            _task_property_bool.task_type_property=p
                                            _task_property_bool.value=True
                                            _task_property_bool.save()


                            
                        context["Message"] = "ذخیره شد"

                        if (not request.POST["previous_page"]==""):
                            return HttpResponseRedirect(request.META.get('HTTP_REEFER',request.POST["previous_page"]))
                        else:
                            return redirect("tasks:task_profile", task.id )


                else:
                    raise PermissionDenied    
           
        except Exception as ex:
            if len(ex.args):
                context["Error"] = ex.args[0]
            else:
                context["Error"] = 'Unknown'
    
    try:
        task = Task.objects.get(pk=id)

        isCreator=False
        isCreatorParent=False
        isAssignee=False
        isAssigneeParent=False
        isGrandParent=False

        if (task.creator.id==request.user.id):
            isCreator=True

        if (as_user.id in task.creator.employee.GetEmployeeParentSet or as_user == task.creator):
            isCreatorParent=True
        
        if(task.user_assignee or task.group_assignee):
            
            if((task.user_assignee== request.user) or (task.group_assignee and task.group_assignee.head== request.user )):
                isAssignee=True

            
            if((task.user_assignee and task.user_assignee.employee.GetEmployeeParent == as_user.id) or (task.group_assignee and task.group_assignee.head.employee.GetEmployeeParent == as_user.id)):
                isAssigneeParent=True
            try:
                _user_id=0
                if task.user_assignee:
                    _user_id=task.user_assignee.employee.GetEmployeeParent
                if task.group_assignee:
                    _user_id=task.group_assignee.head.employee.GetEmployeeParent
                employe_parent=Employee.objects.get(user__id=_user_id)
                if(as_user.id in employe_parent.GetEmployeeParentSet):
                    isGrandParent=True
            except:
                pass
            
        context["task"] = task
        if request.method == "GET":
            context["task_current"]=task.current
            context["startdate"] = ConvertToSolarDate(task.startdate)
            context["enddate"] = ConvertToSolarDate(task.enddate)
        else:
            if "task_edit_current" in request.POST:
                context["task_current"]=True
            else:
                context["task_current"]=False
                context["startdate"] = request.POST["startdate"]
                context["enddate"] = request.POST["enddate"]
        context["task_type"] = task.task_type_id
        context["task_level"] = task.task_level_id
        context["task_parent"] = task.task_parent_id
        
        context['task_level_list'] = Task_Level.objects.all()
        context['task_type_list'] = Task_Type.objects.all()
        context["task_portion_in_parentInputId"] = task.task_portion_in_parent
        context["ProgressInputId"] = task.progress
        
        try:
            context["children_user"]=User.objects.filter(is_active=True).filter(Q(pk__in=task.creator.employee.GetDirectChildrenUserId)|Q(pk=task.creator.id)).exclude(username='admin').order_by('last_name')
        except:
            pass
        context["users"] = User.objects.filter(is_active=True).exclude(username='admin').order_by('last_name')
        context["task_groups"] = Task_Group.objects.filter(creator=task.creator)

        context["task_type_property"]=Task_Type_Property.objects.filter(task_type=task.task_type)
        context["task_type_property_num"]=Task_Property_Num.objects.filter(task=task,deleted=False)
        context["task_type_property_text"]=Task_Property_Text.objects.filter(task=task,deleted=False)
        context["task_type_property_date"]=Task_Property_Date.objects.filter(task=task,deleted=False)
        context["task_type_property_file"]=Task_Property_File.objects.filter(task=task,deleted=False)
        context["task_type_property_bool"]=Task_Property_Bool.objects.filter(task=task,deleted=False)
        
        context["resources"]=Resource.objects.filter(Q(pk__in=ResourceAssignment.objects.filter(Q(assignee=as_user)|Q(assignee__pk__in=as_user.employee.GetAllChildrenUserId)).values('resource__pk')))
        context["task_resources"]=ResourceTaskAssignment.objects.filter(task__id=id)
        
               
        context["task_times"]=TaskTime.objects.filter(task__id=id).order_by('-start')
        context["reports"]=Report.objects.filter(task_time__task__id=id)
        property_keys=set()
        for p in Task_Property_Num.objects.filter(task=task,deleted=False):
            property_keys.add(p.task_type_property.id)
        for p in Task_Property_Text.objects.filter(task=task,deleted=False):
            property_keys.add(p.task_type_property.id)
        for p in Task_Property_Date.objects.filter(task=task,deleted=False):
            property_keys.add(p.task_type_property.id)
        for p in Task_Property_File.objects.filter(task=task,deleted=False):
            property_keys.add(p.task_type_property.id)
        for p in Task_Property_Bool.objects.filter(task=task,deleted=False):
            property_keys.add(p.task_type_property.id)
        context["property_keys"]=property_keys

        _task_prerequisite=Task_Prerequisite.objects.filter(task=task)
        id_list=""
        name_list=""
        for pre in _task_prerequisite:
            id_list+=str(pre.prerequisite.id) + ","
            name_list+=pre.prerequisite.name + ","
        id_list=id_list[:-1]
        name_list=name_list[:-1]

        context["prerequisite_name"] =name_list
        context["prerequisite_key"] = id_list

        if task.assign_status==3:
            _requests=task.task_assign_requests.all()
            _request_keys=""
            _request_names=""
            for r in _requests:
                _request_keys+=str(r.id)+","
                _request_names+=r.user.first_name+" "+r.user.last_name+","
            context["request_keys"]=_request_keys[:-1]
            context["request_names"]=_request_names[:-1]
        
        
        tasks = Task.objects.filter(
            Q(user_assignee=task.creator)| Q(group_assignee__head=task.creator)).exclude(cancelled=True).exclude(confirmed=True)
        context['task_Parent_list'] = tasks
        _tree = ""
        children_set=set()
        for t in tasks:
            if t.task_parent is None or (t.task_parent not in tasks and t.task_parent is not None):
                _tree += "<ul class='myUL'>"
                _tree += getchildren(t.pk, tasks)
                _tree += " </ul>"
                children_set.add(t.pk)
        context["tree"] = _tree
    except Exception as ex:
        context["Error"] = ex.args[0]
    # files
    try:
        _files = Task_Attachment.objects.filter(task_id=id)
        context["files"] = _files
    except Exception as ex:
        pass
    # statistics
    try:
        task = Task.objects.get(pk=id) 
        all_task_ids = task.GetAllTaskChildrenId
        all_task_ids.add(task.id)
        task_times = TaskTime.objects.filter(task__pk__in=all_task_ids).exclude(start=None, end=None)
        users_task_time = {}
        users_task_time_score_multiply = {}
        user_contribution = {}
        user_efficiency_percent = {}
        task_all_time = 0
        task_all_score = 0
        
        for item in task_times:
            if item.user.get_full_name() in users_task_time:
                days,seconds=item.Duration.days , item.Duration.seconds
                duration=days * 24 * 60 * 60 + seconds
                users_task_time[item.user.get_full_name()] +=duration
                try:
                    users_task_time_score_multiply[item.user.get_full_name()] += duration * item.task.score
                except:
                    users_task_time_score_multiply[item.user.get_full_name()] += duration * 5
            else:
                days,seconds=item.Duration.days , item.Duration.seconds
                duration=days * 24 * 60 * 60 + seconds
                users_task_time[item.user.get_full_name()] = duration
                try:
                    users_task_time_score_multiply[item.user.get_full_name()] = duration * item.task.score 
                except:
                    users_task_time_score_multiply[item.user.get_full_name()] = duration * 5

        for u in users_task_time:
            task_all_time += users_task_time[u]

        for u in users_task_time_score_multiply:
            task_all_score += users_task_time_score_multiply[u]    

        for u in users_task_time:
            user_contribution[u] = round((users_task_time[u] / task_all_time) * 100, 2)
            users_task_time[u] =ConvertTimeDeltaToStringTime( datetime.timedelta(seconds=users_task_time[u]))
        
        for u in users_task_time_score_multiply:
            user_efficiency_percent[u] =round((users_task_time_score_multiply[u] / task_all_score) *100, 2)

        context["user_all_time"] = users_task_time
        context["user_time_percent"] = user_contribution
        context["user_efficiency"] = user_efficiency_percent            

    except Exception as err:
        context["user_all_time"] = 0
        context["user_time_percent"] = 0
        context["user_efficiency"] = 0 
    


    return render(request, 'Task/edit.html', {'context': context, 'task_id': id,"isCreator":isCreator,"isCreatorParent":isCreatorParent,"isAssignee":isAssignee,"isAssigneeParent":isAssigneeParent,"isGrandParent":isGrandParent})

@login_required(login_url='user:login') #redirect when user is not logged in
def GetSiblingTasks(request,id):
    
    data={}
    try:
        task_parent=id
        if id==0 :
            task_parent=None
        tasks=TaskSerializer(Task.objects.filter(task_parent__id=task_parent,creator=request.user), many=True)
        data["tasks_sibling"]=JSONRenderer().render(tasks.data).decode("utf-8")  
    except Exception as err:
        data['message']= err.args[0]
    return JsonResponse(data)

@login_required(login_url='user:login') #redirect when user is not logged in
def GetTaskTypeProperty(request,task_type_id):
    data={}
    try:
        task_type_property=Task_Type_PropertySerializer(Task_Type_Property.objects.filter(task_type__id=task_type_id,deleted=False), many=True)
        data["task_type_property"]=JSONRenderer().render(task_type_property.data).decode("utf-8")  
    except Exception as err:
        data['message']= err.args[0]
    return JsonResponse(data)

@login_required(login_url='user:login') #redirect when user is not logged in
def TaskProgresschange(request,task_id,amount,explicit="No"):
    data={}
    try:
        if len(request.user.locumtenens_organization_groups.all())>0 and request.user.locumtenens_organization_groups.first().locumtenens_active:
            as_user = request.user.locumtenens_organization_groups.first().manager
        else:
            as_user = request.user

        _user = request.user
        task=Task.objects.get(pk=task_id,cancelled=False,confirmed=False)
        if task.user_assignee == _user or (task.group_assignee and task.group_assignee.head == _user) or \
            ( task.user_assignee and task.user_assignee.employee.GetEmployeeParent == _user.id and task.progress==100)or\
                ( task.group_assignee and task.group_assignee.head.employee.GetEmployeeParent == _user.id and task.progress==100) or \
                    task.user_assignee == as_user or (task.group_assignee and task.group_assignee.head == as_user) or \
                        ( task.user_assignee and task.user_assignee.employee.GetEmployeeParent == as_user.id and task.progress==100)or\
                            ( task.group_assignee and task.group_assignee.head.employee.GetEmployeeParent == as_user.id and task.progress==100):
            if (task.progress>=0 and task.progress<=100 and not task.confirmed and not task.cancelled and not task.progress_autocomplete):
                # #------------------change task category
                # if task.progress==0 and amount>0 and amount<=100:
                #     task.dashboard_category=None
                #     task.save()
                # if task.progress==100 and amount>=0 and amount<100:
                #     task.dashboard_category=None
                #     task.save()
                # if task.progress>0 and task.progress<100 and (amount==0 or amount==100):
                #     task.dashboard_category=None
                #     task.save()
                # #-------------------------------


                Prerequisite=True
                if (task.prerequisite_type == None):
                    Prerequisite=False
                elif (task.prerequisite_type==1):
                    if(len(task.prerequisites.all())==len(task.prerequisites.filter(progress__gt=0))):
                        Prerequisite=False
                elif (task.prerequisite_type==2):
                    if(len(task.prerequisites.filter(progress__gt=0))>0):
                        Prerequisite=False
                _new_amount=0
                if(Prerequisite == False):
                    if(amount>0 or explicit=="Yes"):
                        if(explicit=="Yes"):
                            if (amount>100):
                                _new_amount=100
                            else:
                                _new_amount=amount                           
                        else:
                            _new_amount=(task.progress+1) if (task.progress<100) else task.progress
                    else:
                        _new_amount=(0) if (task.progress-1<=0) else task.progress-1
                    task.SetProgressValue(_new_amount)

                    ################# set task profile amount ############
                    _today = datetime.date.today()
                    try:
                        task_progress = TaskProgress.objects.get(task=task , progress_date=_today)
                        task_progress.progress_value = _new_amount
                        task_progress.save()
                    except:
                        task_progress = TaskProgress()
                        task_progress.progress_value = _new_amount
                        task_progress.user = request.user
                        task_progress.task = task 
                        task_progress.progress_date = _today
                        task_progress.save()


                else:
                    data['message']= "اصول پیش نیاز این کار رعایت نشده است"
        else:    
            raise PermissionDenied
            
        if task.progress_autocomplete:
            data['message']="پیشروی خودکار برای این کار فعال شده است"
        data["progress_value"]=task.progress
        data["progress_color"]=task.ProgressColor
        if task.task_parent:
            data["parents"]= task.task_parent.GetNewProgressAndColor
    except Exception as err:
        data['message']= err.args[0]
    return JsonResponse(data)

@login_required(login_url='user:login') #redirect when user is not logged in
def TaskConfirm(request,task_id,score):
    data={}
    try:
        if len(request.user.locumtenens_organization_groups.all())>0 and request.user.locumtenens_organization_groups.first().locumtenens_active:
            as_user = request.user.locumtenens_organization_groups.first().manager
        else:
            as_user = request.user

        task=Task.objects.get(pk=task_id,cancelled=False,confirmed=False)
        if (task.user_assignee and task.user_assignee.employee.GetEmployeeParent == request.user.id ) or (task.group_assignee and task.group_assignee.head.employee.GetEmployeeParent == request.user.id ):
            task.confirmed=True
            task.confirmed_date=datetime.datetime.now()
            task.score = score
                
            task.save()
   
    except Exception as err:
        data['message']= err.args[0]
    return JsonResponse(data)

def GetChildrenInDashboard(id):
    task = Task.objects.get(pk=id)
    tasks = Task.objects.filter(task_parent_id=id, progress__gt=0,progress__lt=100).exclude(cancelled=True)
    s = "<li  class='nodes_dashboard' type='private' task_name='"+str(task.name).replace("<","&lt;").replace(">","&gt;") +"' task_id=" + \
        str(task.pk)+">"+("<span class='caret_dashboard'>"+str(task.name).replace("<","&lt;").replace(">","&gt;") +"</span>" if not task.public else task.name.replace("<","&lt;").replace(">","&gt;"))
    if len(tasks) > 0:
        s += "<ul class='nested_dashboard'>"
        for ch in tasks:
            _children = Task.objects.filter(task_parent_id=ch.id)
            if len(_children) == 0:
                s += "<li class='nodes_dashboard' task_id="+str(ch.pk)+" type='private'  task_name='"+str(ch.name).replace("<","&lt;").replace(">","&gt;") +"'>"+str(ch.name).replace("<","&lt;").replace(">","&gt;") +"</li>"
            else:
                s += GetChildrenInDashboard(ch.pk)
        s += "</ul>"
    s += "</li>"
    return (s)

@login_required(login_url='user:login') #redirect when user is not logged in
def GetUserAssigneeTask(request):
    data=""
    try:
        tasks = Task.objects.filter(user_assignee=request.user,cancelled=False, confirmed=False, progress__gt=0,progress__lt=100)
        tasks |= Task.objects.filter(group_assignee__head=request.user,cancelled=False, confirmed=False, progress__gt=0,progress__lt=100)
        tasks |= Task.objects.filter(public=True, cancelled = False)
        public_tasks=PublicTask.objects.all()
        _tree = ""
        _tree += "<ul class='main_task_tree'>"
        for t in tasks:
            if t.task_parent is None or (t.task_parent not in tasks and t.task_parent is not None):
                _tree += GetChildrenInDashboard(t.pk)
        # _tree+="<hr>"
        # for _public in public_tasks:
        #     _tree+="<li class='nodes_dashboard' task_id="+str(_public.pk)+" type='public'  task_name='"+_public.name+"'>"+_public.name+"</li>"
        _tree += " </ul>"
        data = _tree
    except:
        pass
    return HttpResponse(data)

#-------------------------------------------------------add resource to task -----------------
@login_required(login_url='user:login') #redirect when user is not logged in
def AddResourceToTask(request,task_id,resource_id):
    data={}
    _user = request.user

    if len(request.user.locumtenens_organization_groups.all())>0 and request.user.locumtenens_organization_groups.first().locumtenens_active:
        as_user = request.user.locumtenens_organization_groups.first().manager
    else:
        as_user = request.user
    
    try:
        _resource_task_assignment=ResourceTaskAssignment()
        _task=Task.objects.get(pk=task_id)
        _resource=Resource.objects.get(pk=resource_id)
        
        _resource_task_assignment.assigner=request.user
        _resource_task_assignment.task=_task
        _resource_task_assignment.resource=_resource

        resources = Resource.objects.filter(Q(pk__in=ResourceAssignment.objects.filter(Q(assignee=as_user)|Q(assignee__pk__in=as_user.employee.GetAllChildrenUserId)).values('resource__pk')))
        if _resource not in resources:
            raise PermissionDenied

        #Access Control
        if ( _task.user_assignee and _task.user_assignee == as_user) or ( _task.user_assignee and as_user.id in _task.user_assignee.employee.GetEmployeeParentSet) \
            or _task.creator == as_user or as_user.id in _task.creator.employee.GetEmployeeParentSet or (_task.group_assignee and _task.group_assignee.head == request.user) \
                or (_task.group_assignee and _task.id in request.user.employee.UnderTaskGroupTasks):
            _resource_task_assignment.save()
        else:
            raise PermissionDenied
        ################################################## Notification
        notification=Notification()
        notification.title="افزودن منبع "+_resource.name +" به کار "+_task.name
        if _task.user_assignee :
            notification.user=_task.user_assignee
        if _task.group_assignee:
            notification.user=_task.group_assignee.head
        notification.displaytime=datetime.datetime.now()
        notification.messages="درتاریخ "+ ConvertToSolarDate(datetime.datetime.now())+" منبع "+_resource.name +" به کار "+_task.name +"تخصیص داده شد"
        notification.link="/task/"+str(_task.pk)+"/profile/"
        notification.save()
        _resource_task_assignment.assignee_notification=notification
        _resource_task_assignment.save()
        ################################################## Notification

        data['message']="تخصیص منبع با موفقیت ذخیره شد"        
    except Exception as err:
        data['message']="خطا در تخصیص منبع" #err.args[0]
            
        
    return JsonResponse(data)

@login_required(login_url='user:login') #redirect when user is not logged in
def GetResourcesOfTask(request,task_id):
    if len(request.user.locumtenens_organization_groups.all())>0 and request.user.locumtenens_organization_groups.first().locumtenens_active:
        as_user = request.user.locumtenens_organization_groups.first().manager
    else:
        as_user = request.user

    data={}
    try:
        task=Task.objects.get(pk=task_id)
        under_task_group_access = False
        if (task.UnderTaskGroup and ( request.user ==  task.UnderTaskGroup.head or task.id in  request.user.employee.UnderTaskGroupTasks)) or\
            (task.UnderTaskGroup and ( as_user ==  task.UnderTaskGroup.head or task.id in  as_user.employee.UnderTaskGroupTasks)):
            under_task_group_access = True
        if task.creator == as_user or task.user_assignee == as_user or as_user.id in task.creator.employee.GetEmployeeParentSet or as_user.id in task.user_assignee.employee.GetEmployeeParentSet or\
            task.id in as_user.employee.CopyFromAccessTasks or under_task_group_access:
            _resources=serializers.serialize('json',Resource.objects.filter(pk__in=ResourceTaskAssignment.objects.filter(task__id=task_id).values('resource__id')))
            data["resources"]=_resources
            data["resources_related"]=serializers.serialize('json',Resource.objects.filter(task=task))
        else:
            raise PermissionDenied
    except Exception as err:
        data['message']=err.args[0]
    return JsonResponse(data)

@login_required(login_url='user:login') #redirect when user is not logged in
def DeleteResourceFromTask(request,task_id,resource_id):
    data={}
    try:
        _resource_task_assignment=ResourceTaskAssignment.objects.get(task__id=task_id,resource__id=resource_id)
        if _resource_task_assignment.assigner == request.user :
            ################################################## Notification
            try:
                notification=Notification.objects.get(pk=_resource_task_assignment.assignee_notification.pk)
                notification.delete()
            except:
                pass
            ################################################## Notification
            _resource_task_assignment.delete()
            data["message"]="حذف با موفقیت انجام شد"
        else:
            raise PermissionDenied
    except Exception as err:
        data['message']=err.args[0]
    return JsonResponse(data)

@login_required(login_url='user:login') 
def GetTaskDetail(request,task_id):
    data={}
    _user = request.user
    _loc_user = None
    try:
        _loc_user = request.user.locumtenens_organization_groups.first().manager
    except:
        pass
    task=Task.objects.get(pk=task_id)
    if task.user_assignee == _user or task.creator==_user or (_user.id in task.creator.employee.GetEmployeeParentSet) or (task.user_assignee and _user.id in task.user_assignee.employee.GetEmployeeParentSet)or \
        task.id in request.user.employee.CopyFromAccessTasks or task.id in request.user.employee.UnderTaskGroupTasks or(task.group_assignee and task.group_assignee.head.id == request.user):
        requested_task = Task_DetailSerializer(Task.objects.get(pk=task_id)).data
        data["task"]=JSONRenderer().render(requested_task).decode("utf-8") 
        return JsonResponse(data)
    elif _loc_user and (task.user_assignee == _loc_user or task.creator==_loc_user or (_loc_user.id in task.creator.employee.GetEmployeeParentSet) or (task.user_assignee and _loc_user.id in task.user_assignee.employee.GetEmployeeParentSet)or \
        task.id in _loc_user.employee.CopyFromAccessTasks) and len(request.user.locumtenens_organization_groups.all())>0 and \
            request.user.locumtenens_organization_groups.first().locumtenens_active:
        requested_task = Task_DetailSerializer(Task.objects.get(pk=task_id)).data
        data["task"]=JSONRenderer().render(requested_task).decode("utf-8") 
        return JsonResponse(data)
    else:
        PermissionDenied

@login_required(login_url='user:login') 
def GetTaskAttachment(request,task_id):
    if len(request.user.locumtenens_organization_groups.all())>0 and request.user.locumtenens_organization_groups.first().locumtenens_active:
        as_user = request.user.locumtenens_organization_groups.first().manager
    else:
        as_user = request.user

    data={}
    _user = request.user
    task=Task.objects.get(pk=task_id)
    under_task_group_access = False
    if (task.UnderTaskGroup and ( _user ==  task.UnderTaskGroup.head or task.id in  _user.employee.UnderTaskGroupTasks)) or\
        (task.UnderTaskGroup and ( as_user ==  task.UnderTaskGroup.head or task.id in  as_user.employee.UnderTaskGroupTasks)):
        under_task_group_access = True

    if task.user_assignee == as_user or task.creator==as_user or (as_user.id in task.creator.employee.GetEmployeeParentSet) or (as_user.id in task.user_assignee.employee.GetEmployeeParentSet)\
        or under_task_group_access or task.id in as_user.employee.CopyFromAccessTasks:
        requested_task = Task_DetailSerializer(Task.objects.get(pk=task_id)).data
        data["task"]=JSONRenderer().render(requested_task).decode("utf-8") 
        return JsonResponse(data)
    else:
        PermissionDenied

@login_required(login_url='user:login') 
def GetTaskTypePropertyWithValue(request,task_id):
    if len(request.user.locumtenens_organization_groups.all())>0 and request.user.locumtenens_organization_groups.first().locumtenens_active:
        as_user = request.user.locumtenens_organization_groups.first().manager
    else:
        as_user = request.user

    data={}
    _user = request.user
    task=Task.objects.get(pk=task_id,cancelled=False,confirmed=False)
    under_task_group_access = False
    if (task.UnderTaskGroup and ( _user ==  task.UnderTaskGroup.head or task.id in  _user.employee.UnderTaskGroupTasks)) or\
        (task.UnderTaskGroup and ( as_user ==  task.UnderTaskGroup.head or task.id in  as_user.employee.UnderTaskGroupTasks)):
        under_task_group_access = True

    if task.user_assignee == as_user or task.creator==as_user or (as_user.id in task.creator.employee.GetEmployeeParentSet) or (as_user.id in task.user_assignee.employee.GetEmployeeParentSet)\
        or under_task_group_access or task.id in as_user.employee.CopyFromAccessTasks:
        try:
            if Task_Property_Num.objects.filter(task__id=task_id):
                requested_task_num = Task_Property_NumSerializer(Task_Property_Num.objects.filter(task__id=task_id), many=True)
                data["task_num_value"]=JSONRenderer().render(requested_task_num.data).decode("utf-8")

            if Task_Property_Text.objects.filter(task__id=task_id):
                requested_task_text = Task_Property_TextSerializer(Task_Property_Text.objects.filter(task__id=task_id), many=True)
                data["task_text_value"] = JSONRenderer().render(requested_task_text.data).decode("utf-8")

            if Task_Property_Date.objects.filter(task__id=task_id):
                requested_task_date = Task_Property_DateSerializer(Task_Property_Date.objects.filter(task__id=task_id), many=True)
                data["task_date_value"] = JSONRenderer().render(requested_task_date.data).decode("utf-8")

            if Task_Property_File.objects.filter(task__id=task_id):
                requested_task_file= Task_Property_FileSerializer(Task_Property_File.objects.filter(task__id=task_id), many=True)
                data["task_file_value"] = JSONRenderer().render(requested_task_file.data).decode("utf-8")        

            if Task_Property_Bool.objects.filter(task__id=task_id):
                requested_task_bool= Task_Property_BoolSerializer(Task_Property_Bool.objects.filter(task__id=task_id), many=True)
                data["task_bool_value"] = JSONRenderer().render(requested_task_bool.data).decode("utf-8")        
        except Exception as err:
            data['message']=err.args[0]
        return JsonResponse(data)
    else:
        PermissionDenied


@login_required(login_url='user:login') 
def TaskProfileShow(request , task_id):
    task=Task.objects.get(pk=task_id)
    if task.task_type and task.task_type.name =="هدف مهندسی اجتماعی" : 
        result = SocialTaskProfile(request , task_id)
    else:
        result = DefaultTaskProfile(request,task_id)
    return render(result[0],result[1],result[2])

# task profile page 
@login_required(login_url='user:login') 
def DefaultTaskProfile(request , task_id):
    if len(request.user.locumtenens_organization_groups.all())>0 and request.user.locumtenens_organization_groups.first().locumtenens_active:
        as_user = request.user.locumtenens_organization_groups.first().manager
    else:
        as_user = request.user

    context={}
    request.session["activated_menu"]="tasks"
    _user = request.user
    task=Task.objects.get(pk=task_id)
    under_task_group_access = False
    if (task.UnderTaskGroup and ( _user ==  task.UnderTaskGroup.head or task.id in  _user.employee.UnderTaskGroupTasks)):
        under_task_group_access = True
    if not(task.user_assignee == as_user or task.creator==as_user or (as_user.id in task.creator.employee.GetEmployeeParentSet) or (task.user_assignee and as_user.id in task.user_assignee.employee.GetEmployeeParentSet) or under_task_group_access or task.id in as_user.employee.CopyFromAccessTasks):
        raise(PermissionDenied)

    if task.user_assignee == as_user or (task.group_assignee and task.group_assignee.head==request.user) or task.creator==as_user or (as_user.id in task.creator.employee.GetEmployeeParentSet) or (task.user_assignee and as_user.id in task.user_assignee.employee.GetEmployeeParentSet)or (task.id in request.user.employee.UnderTaskGroupTasks):
        context["has_edit_access"] = True
    else :
        context["has_edit_access"] = False
        
    try:
        task = Task.objects.get(pk=task_id)
        context["task"] = task
        if task.user_assignee:
            context["task_user_assignee"]=task.user_assignee
            context["task_user_fullname"] = task.user_assignee.get_full_name()

        if task.group_assignee:
            context["task_group_assignee"]=task.group_assignee
            context["task_group_assignee_name"]=task.group_assignee.name
            context["task_user_assignee"]=task.group_assignee.head
        context["task_name"] = task.name
        context["task_description"] = task.description 
        
        # task_progress_data points that user change the progress bar
        task_progress_data={}
        try:
            task_time_progress = TaskProgress.objects.filter(task=task)
            for i in task_time_progress:
                _date = ConvertToSolarDate(i.progress_date)   # changes date
                task_progress_data[_date] = i.progress_value  #changes value

            # task_progress_all_data contains all points in chart
            task_progress_all_data = {}

            task_time_progress_len = len(task_time_progress)
            progress_first_day = task_time_progress[0].progress_date      # first change date 
            progress_last_day = task_time_progress[task_time_progress_len-1].progress_date   # last change date
            task_start_day = task.startdate     # task start date determined by user
            task_end_day = task.enddate         # task end date determined by user
            
            # progress current day is current point we want to add into task progress all data
            if task_start_day:
                progress_current_day = task_start_day
                # if task start day is less lower than task first progress change , this part of code runs
                while progress_current_day < progress_first_day.date():
                    i_solar = ConvertToSolarDate(progress_current_day)     # i_solar is solar date of current day. 
                    task_progress_all_data[i_solar] = ""                   # while current day is lower than first change day, progress value is filled by null or empty value
                    progress_current_day = progress_current_day + datetime.timedelta(days=1)
                

            # progress days is days from first change to last change
            progress_days = []
            progress_days.append(progress_first_day)
            progress_current_day = progress_first_day
            if progress_first_day != progress_last_day:
                while progress_current_day < progress_last_day:
                    progress_current_day = progress_current_day + datetime.timedelta(days=1)
                    progress_days.append(progress_current_day)                    
            
            # current value is the changes has been occured in progress bar
            if progress_first_day:
                current_value = task_progress_data[ConvertToSolarDate(progress_first_day)]  
            for i in progress_days:
                i_solar = ConvertToSolarDate(i)
                if i_solar in task_progress_data:          # when point exist in database
                    current_value =  task_progress_data[i_solar]
                    task_progress_all_data[i_solar] = current_value
                else:
                    task_progress_all_data[i_solar] = current_value   # when point dosn't exist in data base we make last change as this point change
            
            # if last change date is lower than task end date this part of code runs
            if task_end_day:
                while progress_current_day.date() < task_end_day:
                    progress_current_day = progress_current_day + datetime.timedelta(days=1)
                    i_solar = ConvertToSolarDate(progress_current_day)
                    task_progress_all_data[i_solar] = ""      # if no change occured we fill this point value by null or empty
        
        except:
            task_progress_data[0]=0
        if task_progress_all_data:
            context["task_progress"] = task_progress_all_data
            
            
            if task_start_day:
                if task_start_day > progress_first_day.date():
                    task_start_delta_time =  task_start_day - progress_first_day.date()
                    context["task_start_delta"] = task_start_delta_time.days + 1 
                    context["task_start_day"] = ConvertToSolarDate(task_start_day)[5:]
                else:
                    context["task_start_day"] = ConvertToSolarDate(task_start_day)[5:]
                    context["task_start_delta"] = 1
            else:
                context["task_start_day"] = ConvertToSolarDate(progress_first_day)[5:]
                context["task_start_delta"] = 1
            
            if task_end_day:
                if task_start_day and task_start_day < progress_first_day.date():
                    task_end_delta_time =  task_end_day - task_start_day
                    context["task_end_delta"]= task_end_delta_time.days + 1
                    context["task_end_day"] = ConvertToSolarDate(task_end_day)[5:] 
                else:
                    context["task_end_day"] = ConvertToSolarDate(task_end_day)[5:] 
                    task_end_delta_time =  task_end_day - progress_first_day.date()
                    context["task_end_delta"]= task_end_delta_time.days + 1
            else:
                if task_start_day and task_start_day < progress_first_day.date():
                    task_end_delta_time =  progress_last_day.date() - task_start_day
                    context["task_end_delta"]= task_end_delta_time.days + 1
                    context["task_end_day"] = ConvertToSolarDate(progress_last_day)[5:]
                else:
                    context["task_end_day"] = ConvertToSolarDate(progress_last_day)[5:] 
                    task_end_delta_time =  progress_last_day.date() - progress_first_day.date()
                    context["task_end_delta"]= task_end_delta_time.days + 1



        else:
            context["task_progress"] = {"0000/00/00":""}
            context["task_start_day"] = "00/00"
            context["task_start_delta"] = 1
            context["task_end_delta"]=  1
            context["task_end_day"] = "00/00"

        #in this part we want to calculate task parent portion
        family_weight=0
        if task.task_parent:
            this_task_parent=task.task_parent
            task_family= this_task_parent.GetTaskChildrenId   # give task and its siblings
            for i in task_family:                             # this loop gives sum of task and its siblings weight in parent
                t = Task.objects.get(pk = i)
                family_weight += t.task_portion_in_parent     
        else:
            family_weight=1
        this_task_percent=(task.task_portion_in_parent/family_weight) * 100
        context["task_parent_portion"] = round(this_task_percent,1)
        context["task_periority"] = task.task_priority
        context["task_child_number"] = len(task.GetTaskChildrenId)
        
        # part of calculation task direct children
        task_children_list=[]
        for i in task.GetTaskChildrenId:
            t = Task.objects.get(pk = i)
            task_children_list.append(t)
        context["task_children"] = task_children_list

        context["task_attachments"] = Task_Attachment.objects.filter(task = task)
        context["task_resources"] = ResourceTaskAssignment.objects.filter(task__id=task_id)

        context["resources_related"]=Resource.objects.filter(task=task)

        context["resources"]=Resource.objects.filter(Q(pk__in=ResourceAssignment.objects.filter(Q(assignee=as_user)|Q(assignee__pk__in=as_user.employee.GetAllChildrenUserId)).values('resource__pk')))

        # task profile user times filter
        _date_time_now=datetime.datetime.now()
        context["task_profile_this_year"] = 0 
        context["task_profile_this_year_range"]=[]
        context["task_profile_this_year_range"].append('همه')
        context["task_profile_this_year_range"].append('سال جاری')
        years=range(int(ConvertToSolarDate(_date_time_now).split("/")[0])-1 ,int(ConvertToSolarDate(_date_time_now).split("/")[0])-10 ,-1)
        for i in years:
            context["task_profile_this_year_range"].append(i)
        context["task_profile_this_month"] = 0
        #calculate all times spent to this task and its children by users
        try:
            all_task_ids = task.GetAllTaskChildrenId
            all_task_ids.add(task.id)                     # add current task to task children
            task_times = TaskTime.objects.filter(task__pk__in=all_task_ids).exclude(start=None, end=None)
            users_task_time = {}            # user task times without weight
            users_task_time_score_multiply = {}    # user task times with weight
            task_all_time = 0
            task_all_score = 0
            
            
            for item in task_times:
                if item.user.get_full_name() in users_task_time:       #calculated times for existed user in list 
                    days,seconds=item.Duration.days , item.Duration.seconds
                    duration=days * 24 * 60 * 60 + seconds 
                    users_task_time[item.user.get_full_name()][0] +=duration
                    try:
                        users_task_time_score_multiply[item.user.get_full_name()] += duration * item.task.score
                    except:
                        users_task_time_score_multiply[item.user.get_full_name()] += duration * 5
                else:
                    days,seconds=item.Duration.days , item.Duration.seconds
                    duration=days * 24 * 60 * 60 + seconds
                    users_task_time[item.user.get_full_name()]=[0,0,0,""]         # create an item for non existed user contains [user times , user times percent , user times percent with weight]
                    users_task_time[item.user.get_full_name()][0] = duration
                    try:
                        users_task_time_score_multiply[item.user.get_full_name()] = duration * item.task.score 
                    except:
                        users_task_time_score_multiply[item.user.get_full_name()] = duration * 5
            
            #all times spent for task and its children
            for u in users_task_time:
                task_all_time += users_task_time[u][0]

            #all times spent for task and its children with score(or weight)
            for u in users_task_time_score_multiply:
                task_all_score += users_task_time_score_multiply[u]    

            #calculate user times percentage in all times and convert timedelta to time string format
            for u in users_task_time:
                users_task_time[u][1] = int(round((users_task_time[u][0] / task_all_time) * 100, 0))
                users_task_time[u][0] =ConvertTimeDeltaToStringTime( datetime.timedelta(seconds=users_task_time[u][0]))

            #calculate user times percentage in all times with score
            for u in users_task_time_score_multiply:
                users_task_time[u][2] = int(round((users_task_time_score_multiply[u] / task_all_score) *100, 0))

            context["users_all_time"] = users_task_time
        
        except Exception as err:
            context["users_all_time"] = 0

        task_children_and_self_id = task.GetAllTaskChildrenId
        task_children_and_self_id.add( task.id )
        context["task_reports"] = Report.objects.filter(task_time__task__pk__in = task_children_and_self_id).exclude(report_type =1).exclude(report_type =4).exclude(report_type =5).exclude(report_type =6).exclude(report_type=None) 
        
        context["task_groups"] = Task_Group.objects.filter(creator=request.user)
        context["task_times"]=TaskTime.objects.filter(task__id=task_id)
        context["children_users"]=User.objects.filter(is_active=True).filter(pk__in=task.creator.employee.GetDirectChildrenUserId).exclude(pk=task.user_assignee.id)
        if task.copy_from:
            context["children_tasks_to_copy"] = task.copy_from.children.filter(cancelled=False)
        if request.user == task.creator or (task.creator in request.user.employee.GetEmployeeParentSet):
            context['creator_access'] = True
        
        if(request.user.employee.organization_group.manager==request.user):
            context["isManager"]=True
        else:
            context["isManager"]=False

        if task.last_result:
            context["task_last_result"]=task.last_result
        else:
            context["task_last_result"]="برای این کار نتیجه ای ثبت نشده است."

    except:
        pass
    return (request, 'Task/profile.html', {'context': context, 'task_id': task_id})

@login_required(login_url='user:login') 
def SocialTaskProfile(request , task_id):
    if len(request.user.locumtenens_organization_groups.all())>0 and request.user.locumtenens_organization_groups.first().locumtenens_active:
        as_user = request.user.locumtenens_organization_groups.first().manager
    else:
        as_user = request.user

    context={}
    request.session["activated_menu"]="tasks"
    _user = request.user
    task=Task.objects.get(pk=task_id)
    under_task_group_access = False
    if (task.UnderTaskGroup and ( _user ==  task.UnderTaskGroup.head or task.id in  _user.employee.UnderTaskGroupTasks)):
        under_task_group_access = True
    if not(task.user_assignee == as_user or task.creator==as_user or (as_user.id in task.creator.employee.GetEmployeeParentSet) or (task.user_assignee and as_user.id in task.user_assignee.employee.GetEmployeeParentSet) or under_task_group_access or task.id in as_user.employee.CopyFromAccessTasks):
        raise(PermissionDenied)

    if task.user_assignee == as_user or (task.group_assignee and task.group_assignee.head==request.user) or task.creator==as_user or (as_user.id in task.creator.employee.GetEmployeeParentSet) or (task.user_assignee and as_user.id in task.user_assignee.employee.GetEmployeeParentSet)or (task.id in request.user.employee.UnderTaskGroupTasks):
        context["has_edit_access"] = True
    else :
        context["has_edit_access"] = False
        
    try:
        task = Task.objects.get(pk=task_id)
        context["task"] = task
        if request.user == task.user_assignee:
            context["task_user_assignee"]=task.user_assignee
            context["task_user_fullname"] = task.user_assignee.get_full_name()

        if task.group_assignee:
            context["task_group_assignee"]=task.group_assignee
            context["task_group_assignee_name"]=task.group_assignee.name
            context["task_user_assignee"]=task.group_assignee.head
        context["task_name"] = task.name
        context["task_id"]=task_id
        context["task_description"] = task.description 
        # target_profile_picture
        try:
            target_profile_picture = Task_Property_File.objects.get(task = task , task_type_property__slug = "target_profile_picture")
            context["target_profile_picture"] = target_profile_picture
        except:
            pass
        # target_resume
        try:
            target_resume = Task_Property_File.objects.get(task = task , task_type_property__slug = "target_resume")
            context["target_resume"] = target_resume
        except:
            pass
        # target_linkedin_resume
        try:
            target_linkedin_resume = Task_Property_File.objects.get(task = task , task_type_property__slug = "target_linkedin_resume")
            context["target_linkedin_resume"] = target_linkedin_resume
        except:
            pass       
        # target_phone
        try:
            target_phone = Task_Property_Text.objects.get(task = task , task_type_property__slug = "target_phone")
            context["target_phone"] = target_phone
        except:
            pass  
        # target_country
        try:
            target_country = Task_Property_Text.objects.get(task = task , task_type_property__slug = "target_country")
            context["target_country"] = target_country
        except:
            pass         
        # target_email
        try:
            target_email = Task_Property_Text.objects.get(task = task , task_type_property__slug = "target_email")
            context["target_email"] = target_email
        except:
            pass         
        # target_instagram
        try:
            target_instagram = Task_Property_Text.objects.get(task = task , task_type_property__slug = "target_instagram")
            context["target_instagram"] = target_instagram
        except:
            pass         
        # target_city
        try:
            target_city = Task_Property_Text.objects.get(task = task , task_type_property__slug = "target_city")
            context["target_city"] = target_city
        except:
            pass         
        # target_job
        try:
            target_job = Task_Property_Text.objects.get(task = task , task_type_property__slug = "target_job")
            context["target_job"] = target_job
        except:
            pass         
        # target_facebook
        try:
            target_facebook = Task_Property_Text.objects.get(task = task , task_type_property__slug = "target_facebook")
            context["target_facebook"] = target_facebook
        except:
            pass         
        # target_linkedin
        try:
            target_linkedin = Task_Property_Text.objects.get(task = task , task_type_property__slug = "target_linkedin")
            context["target_linkedin"] = target_linkedin
        except:
            pass         
        # target_communication_status
        try:
            target_communication_status = Task_Property_Text.objects.get(task = task , task_type_property__slug = "target_communication_status")
            context["target_communication_status"] = target_communication_status
        except:
            pass         
        # target_life_summary
        try:
            target_life_summary = Task_Property_Text.objects.get(task = task , task_type_property__slug = "target_life_summary")
            context["target_life_summary"] = target_life_summary
        except:
            pass         
        # target_first_name
        try:
            target_first_name = Task_Property_Text.objects.get(task = task , task_type_property__slug = "target_first_name")
            context["target_first_name"] = target_first_name
        except:
            pass         
        # target_middle_name
        try:
            target_middle_name = Task_Property_Text.objects.get(task = task , task_type_property__slug = "target_middle_name")
            context["target_middle_name"] = target_middle_name
        except:
            pass         
        # target_last_name
        try:
            target_last_name = Task_Property_Text.objects.get(task = task , task_type_property__slug = "target_last_name")
            context["target_last_name"] = target_last_name
        except:
            pass         
        # target_organization
        try:
            target_organization = Task_Property_Text.objects.get(task = task , task_type_property__slug = "target_organization")
            context["target_organization"] = target_organization
        except:
            pass         
        # target_layer_number
        try:
            target_layer_number = int( Task_Property_Num.objects.get(task = task , task_type_property__slug = "target_layer_number"))
            context["target_layer_number"] =target_layer_number
        except:
            pass         
        # target_connector_comments
        try:
            target_connector_comments = Task_Property_Text.objects.get(task = task , task_type_property__slug = "target_connector_comments")
            context["task_profile_user_note_input"] = target_connector_comments
        except:
            pass 
        # identity_profile_picture  
        try:
            identity_profile_picture = ResourcePropertyFile.objects.filter(resource__task_assignement__task = task  , resource_type_property__slug = "identity_profile_picture")
            context["identity_profile_picture"] = identity_profile_picture[0]
        except:
            pass
        # identity_name
        try:
            identity_first_name = ResourcePropertyText.objects.filter(resource__task_assignement__task = task , resource_type_property__slug = "identity_first_name")
            identity_last_name = ResourcePropertyText.objects.filter(resource__task_assignement__task = task , resource_type_property__slug = "identity_last_name")
            context["identity_name"] = identity_first_name[0].value + "  " + identity_last_name[0].value
        except:
            pass 



        all_task_files= Task_Attachment.objects.filter(task = task)
        picture_extension = ["jpg","png","jpeg"]
        pictures = []
        notpicture = []
        for i in all_task_files:
            if i.filename.split(".")[-1].lower() in picture_extension:
                pictures.append(i)
            else:
                notpicture.append(i)

        all_report_pictures = ReportAttachment.objects.filter(report__task_time__task__id = task_id)
        for i in all_report_pictures:
            if i.filename.split(".")[-1].lower() in picture_extension:
                pictures.append(i)
            else:
                notpicture.append(i)

        context["task_attachments"] = notpicture
        context["task_pictures"] = pictures
        context["task_resources"] = ResourceTaskAssignment.objects.filter(task__id=task_id)
        context["resources"]=Resource.objects.filter(Q(pk__in=ResourceAssignment.objects.filter(Q(assignee=as_user)|Q(assignee__pk__in=as_user.employee.GetAllChildrenUserId)).values('resource__pk')))
       
        task_children_and_self_id = task.GetAllTaskChildrenId
        task_children_and_self_id.add( task.id )
        task_reports = Report.objects.filter(task_time__task__pk__in = task_children_and_self_id).exclude(report_type =1).exclude(report_type=None) 

        context["task_reports_event"] = task_reports.filter(report_type = 2)
        context["task_reports_event_number"] = len(context["task_reports_event"])

        context["task_reports_result"] = task_reports.filter(report_type = 3)
        context["task_reports_result_number"] = len(context["task_reports_result"])

        context["task_reports_chat"] = task_reports.filter(report_type = 4)
        context["task_reports_chat_number"] = len(context["task_reports_chat"])

        context["task_reports_file"] = task_reports.filter(report_type = 5)
        context["task_reports_file_number"] = len(context["task_reports_file"])

        context["task_reports_link"] = task_reports.filter(report_type = 6)
        context["task_reports_link_number"] = len(context["task_reports_link"])

        

        context["task_groups"] = Task_Group.objects.filter(creator=request.user)
        context["task_times"]=TaskTime.objects.filter(task__id=task_id)
        context["children_users"]=User.objects.filter(is_active=True).filter(pk__in=task.creator.employee.GetDirectChildrenUserId).exclude(pk=task.user_assignee.id)
        
        if task.copy_from:
            context["children_tasks_to_copy"] = task.copy_from.children.filter(cancelled=False)
        if request.user == task.creator or (task.creator in request.user.employee.GetEmployeeParentSet):
            context['creator_access'] = True
        
        if(request.user.employee.organization_group.manager==request.user):
            context["isManager"]=True
        else:
            context["isManager"]=False



    except:
        pass
    return (request, 'Task/social_taskprofile.html', {'context': context, 'task_id': task_id})



# function to add , edit and show task last result.
@login_required(login_url='user:login') 
def TaskLastResult(request,task_id):
    data={}
    if len(request.user.locumtenens_organization_groups.all())>0 and request.user.locumtenens_organization_groups.first().locumtenens_active:
        as_user = request.user.locumtenens_organization_groups.first().manager
    else:
        as_user = request.user

    task=Task.objects.get(pk=task_id)

    under_task_group_access = False
    if (task.UnderTaskGroup and ( request.user ==  task.UnderTaskGroup.head or task.id in  request.user.employee.UnderTaskGroupTasks)) or\
        (task.UnderTaskGroup and ( as_user ==  task.UnderTaskGroup.head or task.id in  as_user.employee.UnderTaskGroupTasks)):
        under_task_group_access = True
    if not(task.user_assignee == as_user or task.creator==as_user or (as_user.id in task.creator.employee.GetEmployeeParentSet) or (task.user_assignee and as_user.id in task.user_assignee.employee.GetEmployeeParentSet) or under_task_group_access or \
        task.id in as_user.employee.CopyFromAccessTasks ):
        raise(PermissionDenied)

        
    if request.method == "POST":
        if not(task.user_assignee == request.user or task.group_assignee.head == request.user) : # or (task.group_assignee and task.group_assignee.head==request.user) or task.creator==_user or (_user.id in task.creator.employee.GetEmployeeParentSet) or (task.user_assignee and _user.id in task.user_assignee.employee.GetEmployeeParentSet)or (task.group_assignee and _user.id in task.group_assignee.head.employee.GetEmployeeParentSet)):
            raise(PermissionDenied)
        try:
            task = Task.objects.get(pk=task_id)
            if "task_profile_last_result_input" in request.POST:
                task.last_result=request.POST["task_profile_last_result_input"]
                task.save()
            data["task_profile_last_result_input"]=task.last_result
            return JsonResponse(data)
        except:
            pass
    
    try:
        task = Task.objects.get(pk=task_id)
        data["task_profile_last_result_input"]=task.last_result
    except:
        data["task_profile_last_result_input"]= " آخرین وضعیت کار ثبت نشده است."

    return JsonResponse(data)

# function to add new comment to a task
@login_required(login_url='user:login') #redirect when user is not logged in
def AddComment(request , task_id):
    data={}
    if request.method=="POST":
        try:
            comment=TaskComment()
            comment.content=request.POST["task_profile_comment_new_message_input"]
            task=Task.objects.get(pk=int(task_id))
            assignee_access = False
            if len(request.user.locumtenens_organization_groups.all())>0 and request.user.locumtenens_organization_groups.first().locumtenens_active:
                as_user = request.user.locumtenens_organization_groups.first().manager
            else:
                as_user = request.user

            try:
                if task.user_assignee == as_user or as_user.id in task.user_assignee.employee.GetEmployeeParentSet :
                    assignee_access = True
            except:
                try:
                    if task.group_assignee.head == request.user or task.id in request.user.employee.UnderTaskGroupTasks or \
                        task.group_assignee.head == as_user or task.id in as_user.employee.UnderTaskGroupTasks:
                        assignee_access = True
                except:
                    pass


            if task.creator == as_user or (as_user.id in task.creator.employee.GetEmployeeParentSet) or assignee_access:
                comment.task=task
                comment.user=request.user
                try:
                    reply_comment = TaskComment.objects.get(pk=int(request.POST["task_profile_comment_reply_input"]))
                    comment.reply_to =reply_comment
                except:
                    pass
                comment.save()
                if comment.reply_to :
                    try:
                        reply_notification=Notification()
                        reply_notification.title="پاسخ ملاحظه نشده (کار) "
                        reply_notification.user=reply_comment.user
                        reply_notification.displaytime=datetime.datetime.now()
                        reply_notification.messages=request.user.first_name+" "+request.user.last_name +" در تاریخ " + ConvertToSolarDate(datetime.datetime.now()) +" پاسخی مربوط به کار  "+ task.name +" ثبت کرده است "
                        reply_notification.link="/task/" + str(task.id) + "/profile/"
                        reply_notification.closed=False
                        reply_notification.save()
                    except:
                        pass

                elif task.user_assignee != request.user:
                    notification=Notification()
                    notification.title="نظر خوانده نشده (کار) "
                    notification.user=task.user_assignee
                    notification.displaytime=datetime.datetime.now()
                    notification.messages=request.user.first_name+" "+request.user.last_name +" در تاریخ " + ConvertToSolarDate(datetime.datetime.now()) +" نظری مربوط به کار  "+ task.name +" ثبت کرده است "
                    notification.link="/task/" + str(task.id) + "/profile/"
                    notification.closed=False
                    notification.save()
                    task.comment_notification=notification
                    task.save()

                data["message"]="نظر شما با موفقیت ثبت شد"
            else:
                raise PermissionDenied
        except Exception as err:
            data['message']=err.args[0]
            
    return JsonResponse(data)

# function to send all task comments to task profile page
@login_required(login_url='user:login') #redirect when user is not logged in
def GetCommentList(request,task_id):
    data={}
    try:
        _user = request.user
        task=Task.objects.get(pk=task_id)
        if len(request.user.locumtenens_organization_groups.all())>0 and request.user.locumtenens_organization_groups.first().locumtenens_active:
            as_user = request.user.locumtenens_organization_groups.first().manager
        else:
            as_user = request.user

        under_task_group_access = False
        if (task.UnderTaskGroup and ( _user ==  task.UnderTaskGroup.head or task.id in  _user.employee.UnderTaskGroupTasks)):
            under_task_group_access = True
        if (task.user_assignee == as_user or task.creator==as_user or (as_user.id in task.creator.employee.GetEmployeeParentSet) or (task.user_assignee and as_user.id in task.user_assignee.employee.GetEmployeeParentSet) or under_task_group_access or \
            task.id in as_user.employee.CopyFromAccessTasks ):
            comments=TaskCommentReplySerializer(TaskComment.objects.filter(task__id=task_id), many=True)
            data["comments"]=JSONRenderer().render(comments.data).decode("utf-8") 
        else:
            raise(PermissionDenied)
        
    except Exception as err:
        data['message']=err.args[0]
            
    return JsonResponse(data)

@login_required(login_url='user:login') #redirect when user is not logged in
def GetCommentReply(request,task_comment_id):
    data={}
    try:
        comment=TaskComment.objects.get(pk=int(task_comment_id))
        task=comment.task
        _user = request.user
        if len(request.user.locumtenens_organization_groups.all())>0 and request.user.locumtenens_organization_groups.first().locumtenens_active:
            as_user = request.user.locumtenens_organization_groups.first().manager
        else:
            as_user = request.user

        under_task_group_access = False
        if (task.UnderTaskGroup and ( _user ==  task.UnderTaskGroup.head or task.id in  _user.employee.UnderTaskGroupTasks)):
            under_task_group_access = True
        if (task.user_assignee == as_user or task.creator==as_user or (as_user.id in task.creator.employee.GetEmployeeParentSet) or (task.user_assignee and as_user.id in task.user_assignee.employee.GetEmployeeParentSet) or \
            under_task_group_access or task.id in as_user.employee.CopyFromAccessTasks ): 
            comment=TaskCommentReplySerializer(comment)           
            data["comment_reply"] = JSONRenderer().render(comment.data).decode("utf-8")
        else:
            raise(PermissionDenied)
        
    except Exception as err:
        data['message']=err.args[0]
            
    return JsonResponse(data)



# function to copy a task for another user to continue working on with access to previous task
@login_required(login_url='user:login')
def TaskCopy(request,task_id):
    data={}
    try:
        _task = Task.objects.get(pk=task_id)
        if _task.creator == request.user or _task.creator in request.user.employee.GetEmployeeParentSet:
            if int(request.POST['copy_user_select']) > 0:
                _new_user = User.objects.get(id = int(request.POST['copy_user_select']))
                if _new_user and _task.user_assignee and _task.user_assignee != _new_user:
                    
                    _task.user_assignee = _new_user
                    _task.name = _task.name + str(len(_task.copies.all())+1)
                    _task.id = None
                    _task.save()
                    _task.copy_from = Task.objects.get(id=task_id)
                    _task.save()

                    data['message']='انتقال با موفقیت انجام شد.'
                else:
                    data['message']='کار قابل انتقال به کاربر انتخاب شده نیست.'
            else:
                data['message']='کاربر جدید انتخاب نشده است.'
        else:
            raise(PermissionDenied)
    except Exception as err:
        data['message']=err.args[0]

    return JsonResponse(data)


# function to copy children of a copied task for another user to continue working on with access to previous task
@login_required(login_url='user:login')
@transaction.atomic
def TaskCopyChildren(request,task_id):
    data={}
    try:
        _task = Task.objects.get(pk=task_id)
        if _task.user_assignee == request.user :
            if len(request.POST.getlist('copy_task_select')) > 0:
                for task_id in request.POST.getlist('copy_task_select'):
                    _new_task = Task.objects.get(id = int(task_id))
                    if _new_task and _new_task in _task.copy_from.children.all() and not _new_task.cancelled:
                        _name_uniq = True
                        for ch in _task.children.all():
                            if ch.name == _new_task.name :
                                _name_uniq = False
                        if _name_uniq :
                            _new_task.name = _new_task.name
                        else :
                            _new_task.name = _new_task.name + '*'
                        
                        _new_task.id = None
                        _new_task.user_assignee = None
                        _new_task.last_result = None
                        _new_task.task_parent = _task
                        _new_task.prerequisite_type = None
                        _new_task.creator = request.user
                        _new_task.task_group = False
                        _new_task.group_assignee = None
                        _new_task.assign_status = None
                        _new_task.progress = 0
                        _new_task.progress_complete_date = None
                        _new_task.confirmed_date = None
                        _new_task.score = None
                        _new_task.startdate = None
                        _new_task.startdate_notification = None
                        _new_task.confirmed = False
                        _new_task.enddate = None
                        _new_task.enddate_notification = None
                        _new_task.created = datetime.datetime.now()
                        _new_task.updated = datetime.datetime.now()
                        _new_task.children_copied = False
                        _new_task.save()
                        _new_task.copy_from = Task.objects.get(id = int(task_id))
                        _new_task.save()

                _task.children_copied= True
                _task.save()
                data['message']='انتقال با موفقیت انجام شد.'
            else:
                data['message']='کار برای انتقال انتخاب نشده است.'
        else:
            raise(PermissionDenied)
    except Exception as err:
        data['message']=err.args[0]

    return JsonResponse(data)

@login_required(login_url='user:login') #redirect when user is not logged in
def GetTaskTypeAutoRequestUsers(request,task_type_id):
    data={}
    try:
        _task_type_auto_requests=Task_Type_Auto_RequestSerializer(Task_Type_Auto_Request.objects.filter(task_type__id=int(task_type_id)) , many=True)

        data["task_type_auto_requests"]=JSONRenderer().render(_task_type_auto_requests.data).decode("utf-8") 
    except Exception as err:
        data['message']=err.args[0]
            
    return JsonResponse(data)

# function to add , edit and show task last result.
@login_required(login_url='user:login') 
def AddUserNote(request,task_id):
    data={}
    if len(request.user.locumtenens_organization_groups.all())>0 and request.user.locumtenens_organization_groups.first().locumtenens_active:
        as_user = request.user.locumtenens_organization_groups.first().manager
    else:
        as_user = request.user

    task=Task.objects.get(pk=task_id)

    under_task_group_access = False
    if (task.UnderTaskGroup and ( request.user ==  task.UnderTaskGroup.head or task.id in  request.user.employee.UnderTaskGroupTasks)) or\
        (task.UnderTaskGroup and ( as_user ==  task.UnderTaskGroup.head or task.id in  as_user.employee.UnderTaskGroupTasks)):
        under_task_group_access = True
    if not(task.user_assignee == as_user or task.creator==as_user or (as_user.id in task.creator.employee.GetEmployeeParentSet) or (task.user_assignee and as_user.id in task.user_assignee.employee.GetEmployeeParentSet) or under_task_group_access or \
        task.id in as_user.employee.CopyFromAccessTasks ):
        raise(PermissionDenied)

        
    if request.method == "POST":
        if not(task.user_assignee == request.user or task.group_assignee.head == request.user) : # or (task.group_assignee and task.group_assignee.head==request.user) or task.creator==_user or (_user.id in task.creator.employee.GetEmployeeParentSet) or (task.user_assignee and _user.id in task.user_assignee.employee.GetEmployeeParentSet)or (task.group_assignee and _user.id in task.group_assignee.head.employee.GetEmployeeParentSet)):
            raise(PermissionDenied)
        try:
            target_connector_comments = Task_Property_Text.objects.get(task = task , task_type_property__slug = "target_connector_comments")
            if "task_profile_user_note_input" in request.POST:
                target_connector_comments.value=request.POST["task_profile_user_note_input"]
                target_connector_comments.save()
            data["task_profile_user_note_input"] = target_connector_comments.value
            return JsonResponse(data)
        except:
            pass
    try:
        target_connector_comments = Task_Property_Text.objects.get(task = task , task_type_property__slug = "target_connector_comments")
        data["task_profile_user_note_input"]=target_connector_comments.value
    except:
        data["task_profile_user_note_input"]= "نظری ثبت نشده است."

    return JsonResponse(data)

@login_required(login_url='user:login') 
def TaskProfileUserStatistics(request , task_id , year , month):

    if year != 0 and year !=1:
        year = int(year)
    elif year == 1:
        year = int(ConvertToSolarDate(datetime.datetime.now()).split("/")[0])
    else:
        year = 0
    month = int(month)
    
    data={}
    data["year"] = year
    data["month"] =  month
    data["task_id"] = task_id
    task=Task.objects.get(pk=task_id)

    # this_user=task.user_assignee
    # if _user !=request.user.id and request.user.id not in this_user.employee.GetEmployeeParentSet:
    #     raise PermissionDenied
    #calculate all times spent to this task and its children by users
    try:

        all_task_ids = task.GetAllTaskChildrenId
        all_task_ids.add(task.id)                     # add current task to task children
        task_times = TaskTime.objects.filter(task__pk__in=all_task_ids).exclude(start=None, end=None)
        
        if year !=0:
            if month !=0:
                #first time and last time in a month
                _first_date_time_in_month = datetime.datetime.strptime(ConvertToMiladi(str(year)+"/"+str(month)+"/1")+" 00:00:00",'%Y-%m-%d %H:%M:%S')
                _last_date_time_in_month=datetime.datetime.strptime(ConvertToMiladi(str(year)+"/"+str(month)+"/1")+" 23:59:00",'%Y-%m-%d %H:%M:%S')
                for i in range(2,32):
                    _last_date_time_in_month+=datetime.timedelta(days=1)
                    if str(ConvertToSolarDate(_last_date_time_in_month).split("/")[1])!=str(month):
                        _last_date_time_in_month-=datetime.timedelta(days=1)

                task_times = task_times.filter(Q(start__gte = _first_date_time_in_month,end__lte = _last_date_time_in_month))      
            else:
                #first time and last time in a year
                _first_date_time_in_month = datetime.datetime.strptime(ConvertToMiladi(str(year)+"/1/1")+" 00:00:00",'%Y-%m-%d %H:%M:%S')
                _last_date_time_in_month=datetime.datetime.strptime(ConvertToMiladi(str(year)+"/12/1")+" 23:59:00",'%Y-%m-%d %H:%M:%S')
                for i in range(2,32):
                    _last_date_time_in_month+=datetime.timedelta(days=1)
                    if str(ConvertToSolarDate(_last_date_time_in_month).split("/")[1])!=str(month):
                        _last_date_time_in_month-=datetime.timedelta(days=1)

                task_times = task_times.filter(Q(start__gte = _first_date_time_in_month,end__lte = _last_date_time_in_month)) 
        else:
            task_times = task_times
        users_task_time = {}            # user task times without weight
        users_task_time_score_multiply = {}    # user task times with weight
        task_all_time = 0
        task_all_score = 0
        
        
        for item in task_times:
            if item.user.get_full_name() in users_task_time:       #calculated times for existed user in list 
                days,seconds=item.Duration.days , item.Duration.seconds
                duration=days * 24 * 60 * 60 + seconds 
                users_task_time[item.user.get_full_name()][0] +=duration
                try:
                    users_task_time_score_multiply[item.user.get_full_name()] += duration * item.task.score
                except:
                    users_task_time_score_multiply[item.user.get_full_name()] += duration * 5
            else:
                days,seconds=item.Duration.days , item.Duration.seconds
                duration=days * 24 * 60 * 60 + seconds
                users_task_time[item.user.get_full_name()]=[0,0,0,""]         # create an item for non existed user contains [user times , user times percent , user times percent with weight]
                users_task_time[item.user.get_full_name()][0] = duration
                try:
                    users_task_time_score_multiply[item.user.get_full_name()] = duration * item.task.score 
                except:
                    users_task_time_score_multiply[item.user.get_full_name()] = duration * 5
        
        #all times spent for task and its children
        for u in users_task_time:
            task_all_time += users_task_time[u][0]

        #all times spent for task and its children with score(or weight)
        for u in users_task_time_score_multiply:
            task_all_score += users_task_time_score_multiply[u]    

        #calculate user times percentage in all times and convert timedelta to time string format
        for u in users_task_time:
            users_task_time[u][1] = int(round((users_task_time[u][0] / task_all_time) * 100, 0))
            users_task_time[u][0] =ConvertTimeDeltaToStringTime( datetime.timedelta(seconds=users_task_time[u][0]))

        #calculate user times percentage in all times with score
        for u in users_task_time_score_multiply:
            users_task_time[u][2] = int(round((users_task_time_score_multiply[u] / task_all_score) *100, 0))

        data["users_all_time"] = users_task_time
    
    except Exception as err:
        data["users_all_time"] = 0
    
    return JsonResponse(data)

@login_required(login_url='user:login') 
def GanttChartPage(request, task_id):
    if len(request.user.locumtenens_organization_groups.all())>0 and request.user.locumtenens_organization_groups.first().locumtenens_active:
        as_user = request.user.locumtenens_organization_groups.first().manager
    else:
        as_user = request.user

    context={}
    request.session["activated_menu"]="tasks"
    _user = request.user
    task=Task.objects.get(pk=task_id)
    if task.current or not(task.startdate) or not(task.enddate) :
        return HttpResponse('نمایش گانت چارت برای کارهای جاری یا فاقد تاریخ شروع و پایان امکان پذیر نیست')
    under_task_group_access = False
    if (task.UnderTaskGroup and ( _user ==  task.UnderTaskGroup.head or task.id in  _user.employee.UnderTaskGroupTasks)):
        under_task_group_access = True
    if not(task.user_assignee == as_user or task.creator==as_user or (as_user.id in task.creator.employee.GetEmployeeParentSet) or (task.user_assignee and as_user.id in task.user_assignee.employee.GetEmployeeParentSet) or under_task_group_access or task.id in as_user.employee.CopyFromAccessTasks):
        raise(PermissionDenied)    
    
    sibling_tasks = Task.objects.filter(task_parent = task.task_parent, current = False).filter( \
        Q(creator=as_user) | Q(user_assignee=as_user)|Q(creator__pk__in=as_user.employee.GetAllChildrenUserId)|Q(user_assignee__pk__in=as_user.employee.GetAllChildrenUserId)|\
            Q(group_assignee__head=request.user)|Q(pk__in=request.user.employee.UnderTaskGroupTasks)|Q(pk__in=as_user.employee.CopyFromAccessTasks)).exclude(pk = task_id).exclude(startdate = None).exclude(enddate = None)



    task_start_date = jdt.datetime.fromgregorian(date = task.startdate)
    task_end_date = jdt.datetime.fromgregorian(date = task.enddate)

    task_duration_days = (task_end_date - task_start_date).days + 1

    
    header_row = "<tr id='gantt_chart_table_header_row'>"
    header_row += "<td id='gantt_task_name_cell' rowspan='2' class='frozen_col' ><select id='gantt_task_name'> <option selected>" + task.name.replace("<","&lt;").replace(">","&gt;") + "</option>"
    for s_task in sibling_tasks :
        header_row += "<option value='" + str(s_task.id) + "'>" + s_task.name.replace("<","&lt;").replace(">","&gt;") + "</option>"
    header_row += "</select></td><td class='frozen-border'><div id='timeline_scroll_right' onclick=\"$('#gantt_chart_main').animate({scrollLeft: '+=150px'}, 800);\"' ></div><div id='timeline_scroll_left' onclick=\"$('#gantt_chart_main').animate({scrollLeft: '-=150px'}, 800);\" ></div></td>"
    
    if task_duration_days > 366 :
        header_row += "<td class='top_time_line' colspan='" + str(365 - task_start_date.yday())  + "' >سال " + str(task_start_date.year) + "</td>"
        years_list = list(range(task_start_date.year + 1, task_end_date.year, 1))
        for year in years_list:
            header_row += "<td class='top_time_line' colspan='" + str(365)  + "' >سال " + str(year) + "</td>"    
        header_row += "<td class='top_time_line' colspan='" + str(task_end_date.yday())  + "' >سال " + str(task_end_date.year) + "</td>"
    else :
        header_row += "<td class='top_time_line' colspan='" + str(jdt.j_days_in_month[task_start_date.month - 1] - task_start_date.day)  + "' >" + jdt.datetime.j_months_fa[task_start_date.month - 1] + str(task_start_date.year) + "</td>"
        temp_month_iterator = task_start_date + jdt.timedelta(jdt.j_days_in_month[task_start_date.month - 1])
        while temp_month_iterator < task_end_date and not(temp_month_iterator.month == task_end_date.month and temp_month_iterator.year == task_end_date.year) :
            header_row += "<td class='top_time_line' colspan='" + str(jdt.j_days_in_month[temp_month_iterator.month - 1])  + "' >" + jdt.datetime.j_months_fa[temp_month_iterator.month - 1] + str(temp_month_iterator.year) + "</td>"
            temp_month_iterator = temp_month_iterator + jdt.timedelta(jdt.j_days_in_month[temp_month_iterator.month - 1])
        header_row += "<td class='top_time_line' colspan='" + str(task_end_date.day)  + "' >" + jdt.datetime.j_months_fa[task_end_date.month - 1] + str(task_end_date.year) + "</td>"

    header_row += "</tr>"


    time_line_row = "<tr id='gantt_chart_table_timeline_row'><td class='frozen-border'>"
    time_line_row_count = 2
    if task_duration_days > 366 :
        width_percent = 16
        time_line_row += "<td class='main_time_line' colspan='" + str(jdt.j_days_in_month[task_start_date.month - 1] - task_start_date.day)  + "' >" + jdt.datetime.j_months_fa[task_start_date.month - 1] + str(task_start_date.year) + "</td>"
        temp_month_iterator = task_start_date + jdt.timedelta(jdt.j_days_in_month[task_start_date.month - 1])
        while temp_month_iterator < task_end_date and not(temp_month_iterator.month == task_end_date.month and temp_month_iterator.year == task_end_date.year) :
            time_line_row += "<td class='main_time_line' colspan='" + str(jdt.j_days_in_month[temp_month_iterator.month - 1])  + "' >" + jdt.datetime.j_months_fa[temp_month_iterator.month - 1] + str(temp_month_iterator.year) + "</td>"
            temp_month_iterator = temp_month_iterator + jdt.timedelta(jdt.j_days_in_month[temp_month_iterator.month - 1])
            time_line_row_count += 1
        time_line_row += "<td class='main_time_line' colspan='" + str(task_end_date.day)  + "' >" + jdt.datetime.j_months_fa[task_end_date.month - 1] + str(task_end_date.year) + "</td>"
    elif task_duration_days > 31 :
        if task_duration_days > 140 :
            width_percent = 10
            time_line_row_count = int(task_duration_days / 15)
            if (jdt.j_days_in_month[task_start_date.month - 1] - task_start_date.day) > 15:
                time_line_row += "<td class='main_time_line' colspan='" + str((jdt.j_days_in_month[task_start_date.month - 1] - task_start_date.day) - 15)  + "' >نیمه اول</td>"
                time_line_row += "<td class='main_time_line' colspan='15' >نیمه دوم</td>"
            else:
                time_line_row += "<td class='main_time_line' colspan='" + str(jdt.j_days_in_month[task_start_date.month - 1] - task_start_date.day)  + "' >نیمه دوم</td>"
            temp_month_iterator = task_start_date + jdt.timedelta(jdt.j_days_in_month[task_start_date.month - 1])
            while temp_month_iterator < task_end_date and not(temp_month_iterator.month == task_end_date.month and temp_month_iterator.year == task_end_date.year) :
                time_line_row += "<td class='main_time_line' colspan='" + str(jdt.j_days_in_month[temp_month_iterator.month - 1] - 15)  + "' >نیمه اول</td>"
                time_line_row += "<td class='main_time_line' colspan='15' >نیمه دوم</td>"
                temp_month_iterator = temp_month_iterator + jdt.timedelta(jdt.j_days_in_month[temp_month_iterator.month - 1])
            if task_end_date.day > 15 :
                time_line_row += "<td class='main_time_line' colspan='15' >نیمه اول</td>"
                time_line_row += "<td class='main_time_line' colspan='" + str(task_end_date.day - 15)  + "' >نیمه دوم</td>"
            else:
                time_line_row += "<td class='main_time_line' colspan='" + str(task_end_date.day)  + "' >نیمه اول</td>"
        else :
            width_percent = 9
            time_line_row_count = int(task_duration_days / 7)
            for i in range(0,int(task_duration_days/7)):
                time_line_row += "<td class='main_time_line' colspan='7' > هفته" + str(i+1) + "</td>"
            if task_duration_days % 7 > 0 :
                time_line_row += "<td class='main_time_line' colspan='" + str(task_duration_days % 7) + "' > هفته" + str(int(task_duration_days/7)+1) + "</td>"
    else :
        width_percent = 6
        time_line_row_count = task_duration_days
        days_list = [ task_start_date + jdt.timedelta(days = x) for x in range(task_duration_days)]
        for day in days_list :
            if day.date() == jdt.datetime.today().date():
                time_line_row += "<td class='main_time_line main_time_line_today' colspan='1' > " + str(day.day)  + "</td>"
            else:
                time_line_row += "<td class='main_time_line' colspan='1' > " + str(day.day)  + "</td>"

    time_line_row += "</tr>"

    chart_table_content = "<table id='gant_chart_main_table' style='width:" + str(time_line_row_count * width_percent) + "%;'><tbody>"
    
    chart_table_content += header_row

    chart_table_content += time_line_row
  

    task_datail_row = "<tr id='gantt_chart_task_detail_row'><td class='frozen_col'><div id='gantt_chart_task_time_info'><div>" + task_start_date.strftime("%d %B %Y") + " - " + task_end_date.strftime("%d %B %Y") + "</div><span>" + str(task.progress) + "% </span></div></td><td class='frozen-border'></td>"
    for i in range(0,task_duration_days+1):
        task_datail_row += "<td class='day-name-det' title='"+ (task_start_date + jdt.timedelta(days = i)).strftime("%d %B %Y") +"'"
        if (task_start_date + jdt.timedelta(days = i)).date() == jdt.datetime.today().date():
            task_datail_row += " rowspan='" + str(Task.objects.all().count()) + "' style='background-image: linear-gradient(90deg, transparent,transparent,transparent,transparent,transparent,#786aff,transparent,transparent,transparent,transparent, transparent);'"
        task_datail_row += "></td>"
    task_datail_row += "</tr>"
    chart_table_content += task_datail_row

    tasks_rows = "<!--" + str(task.id) + "-->"
    child_tasks = Task.objects.filter(task_parent = task, current = False).exclude(startdate = None).exclude(enddate = None).order_by('startdate')
    level = 1
    while child_tasks.count() > 0:
        for _task in child_tasks:
            task_row = "<tr id='gantt_task_row_" + str(_task.id) +"' class='gantt_task_row gantt_task_row_parent_" + str(_task.task_parent.id) + (" display_none" if level > 1 else "") + "' style='font-size:"+ str( int(14 - math.log2(level) * 2 )) +"px;'>"
            task_row += "<td class='frozen_col task_name_td'><span id='gantt_task_expand_" + str(_task.id) +"' class='expand_btn' onclick=\"expand_task(" + str(_task.id) + ");\"></span>"
            task_row += "<span id='gantt_task_collapse_" + str(_task.id) +"' class='collapse_btn display_none' onclick=\"collapse_task(" + str(_task.id) + ");\"></span><div class='task_row_task_name' ondblclick=\"location.href='/task/" + str(_task.id) + "/gantt/';\">" +( "-" * (level -1))+ _task.name.replace("<","&lt;").replace(">","&gt;") + "</div></td><td class='frozen-border'></td>"
            task_row += "<td colspan='" + str((jdt.datetime.fromgregorian(date = _task.startdate) - task_start_date).days) +"'></td>"
            if jdt.datetime.fromgregorian(date = _task.startdate).date() <= jdt.datetime.today().date():
                task_row += "<td colspan='" + str((jdt.datetime.fromgregorian(date = _task.enddate)  - jdt.datetime.fromgregorian(date = _task.startdate) ).days) + "'><div id='gantt_task_timeline_" + str(_task.id) + "' class='gantt_task_timeline' style='background-color:"+str(_task.ProgressColor.replace(',100%,60%',',90%,45%'))+"0.8); height: " + str( int(35 - math.log2(level) * 5))+"px;'>"  
                task_row += "<div class='gantt_task_timeline_progress' style='line-height:" + str( int(35 - math.log2(level) * 5)) + "px;'>" + str(_task.progress) + "%</div><div class='gantt_task_timeline_name' style='line-height:" + str( int(35 - math.log2(level) * 5 )) + "px;'>" + _task.name.replace("<","&lt;").replace(">","&gt;") +"</div><div class='gantt_task_timeline_inner' style='background-color:"+str(_task.ProgressColor.replace(',100%,60%',',90%,45%'))+"1.0);width:" +str(_task.progress)+"%'></div></div></td>"
            else:
                task_row += "<td colspan='" + str((jdt.datetime.fromgregorian(date = _task.enddate)  - jdt.datetime.fromgregorian(date = _task.startdate) ).days) + "'><div id='gantt_task_timeline_" + str(_task.id) + "' class='gantt_task_timeline' style='background-color:"+str(_task.ProgressColor.replace(',100%,60%',',00%,60%'))+"0.8); height: " + str( int(35 - math.log2(level) * 5))+"px;'>"  
                task_row += "<div class='gantt_task_timeline_name' style='line-height:" + str( int(35 - math.log2(level) * 5 )) + "px;'>" + _task.name.replace("<","&lt;").replace(">","&gt;") +"</div><div class='gantt_task_timeline_progress' style='line-height:" + str( int(35 - math.log2(level) * 5)) + "px;'>" + str(_task.progress) + "%</div><div class='gantt_task_timeline_inner' style='background-color:"+str(_task.ProgressColor.replace(',100%,60%',',00%,60%'))+"1.0);width:" +str(_task.progress)+"%'></div></div></td>"
            #task_row += "<td colspan='" + str((task_end_date - jdt.datetime.fromgregorian(date = _task.enddate)).days) + "'></td>"
            task_row += "</tr>" + "<!--" + str(_task.id) + "-->" + "<!--" + str(_task.task_parent.id) + "-->"
            tasks_rows = tasks_rows.replace(("<!--" + str(_task.task_parent.id) + "-->"),task_row)
        child_tasks = Task.objects.filter(task_parent__in = child_tasks, current = False).exclude(startdate = None).exclude(enddate = None).order_by('startdate')
        level += 1
    
    chart_table_content += tasks_rows

    chart_table_content += "</tbody></table>"
    
    context['chart_table_content'] = chart_table_content
    return render(request, 'Task/gantt.html', {'context': context, 'task_id': task_id})

# function that renders automation page
@login_required(login_url='user:login') 
def ListRequests(request):
    if len(request.user.locumtenens_organization_groups.all())>0 and request.user.locumtenens_organization_groups.first().locumtenens_active:
        as_user = request.user.locumtenens_organization_groups.first().manager
        
    else:
        as_user=request.user
    
    request.session["activated_menu"]="requests"
    context = {}

    _archive = False
    if request.GET and request.GET['archive'] == 'True':
        _archive = True
    context["switch_archive"] = _archive

    task_requests=Task_Assign_Request.objects.filter(status=None, task__user_assignee=None,notification_status=None).exclude(need_verification=True).exclude(task__assign_status__lte = 2).exclude(task__cancelled = True).exclude(task__confirmed = True).exclude(task__public = True).filter(Q(user=request.user)|Q(user__in=request.user.employee.GetAllChildrenUserId))
    context["task_requests"]=list(task_requests.values_list('task', flat = True))

    for task_verification in Task_Verification_Log.objects.filter(verified=True):
        if task_verification.last_verifier == None and task_verification.verifier == task_verification.task.creator :
            task_verification.last_verifier = task_verification.task.creator
            task_verification.save()

    if _archive :
        try:
            task_verification_log = Task_Verification_Log.objects.filter(pk = -1)
            if Organization_Group.objects.get(pk=request.user.employee.organization_group.id).locumtenens_active:
                task_verification_log = Task_Verification_Log.objects.filter(Q(verifier=request.user)|Q(verifier_locumtenens=request.user)).exclude(verified=None)
                    
            else:
                task_verification_log = Task_Verification_Log.objects.filter(verifier=request.user).exclude(verified=None)
                    
            context["task_verification_log"]=list(task_verification_log.values_list('task', flat = True))
        except:
            context["task_verification_log"]=None

        context['tasks'] = Task.objects.exclude(assign_status__lte = 2).exclude(public = True).filter(Q(creator=as_user)|Q(pk__in=task_requests.values_list('task', flat = True))|Q(pk__in=task_verification_log.values_list('task', flat = True))).order_by('-pk')

        if request.user.employee.in_staff_group or as_user.employee.GetEmployeeTopParent == as_user:
            context['feedbacks_comment'] = Feedback.objects.filter(feedback_type__needs_verification = True).exclude( comment = None)
        else:
            context['feedbacks_comment'] = Feedback.objects.filter(pk = -1)

        if as_user.employee.GetEmployeeTopParent == as_user:
            context['feedbacks_verif'] = Feedback.objects.filter(feedback_type__needs_verification = True ).exclude( comment = None).exclude(verified = False, rejected = False)
        else:
            context['feedbacks_verif'] = Feedback.objects.filter(pk = -1)

        context['feedbacks_invest'] = Feedback.objects.filter(feedback_type__needs_investigation = True , feedback_type__investigator = request.user , investigated = True)

        context['feedbacks_request'] = Feedback.objects.filter(feedback_type__needs_verification = True , requester = request.user).exclude(verified = False , rejected = False)\
            .exclude(id__in = context['feedbacks_comment'].values_list('pk', flat = True))\
                .exclude(id__in = context['feedbacks_verif'].values_list('pk', flat = True))\
                    .exclude(id__in = context['feedbacks_invest'].values_list('pk', flat = True))

        current_task_requests = Task.objects.filter(pk__in = \
            Task_Assign_Request.objects.filter(status=1,user=request.user).exclude(need_verification=True).values_list('task__id', flat=True), confirmed = True).exclude(cancelled = True)

        context["current_task_requests"] = current_task_requests

    else:
        try:
            task_verification_log = Task_Verification_Log.objects.filter(pk = -1)
            if Organization_Group.objects.get(pk=request.user.employee.organization_group.id).locumtenens_active:
                task_verification_log = Task_Verification_Log.objects.filter(Q(verified=None,verifier=request.user)|Q(verified=None,verifier_locumtenens=request.user))\
                    .filter(pk__in=Task_Verification_Log.objects.values('task').exclude(task__in=Task_Verification_Log.objects.filter(verified=False).values('task'))\
                        .exclude(verified=True).annotate(min_order=Min('verification__order'),id=Min('id')).values('id'))
            else:
                task_verification_log = Task_Verification_Log.objects.filter(Q(verified=None,verifier=request.user))\
                    .filter(pk__in=Task_Verification_Log.objects.values('task').exclude(task__in=Task_Verification_Log.objects.filter(verified=False).values('task'))\
                        .exclude(verified=True).annotate(min_order=Min('verification__order'),id=Min('id')).values('id'))
            context["task_verification_log"]=list(task_verification_log.values_list('task', flat = True))
        except:
            context["task_verification_log"]=None

        context['tasks'] = Task.objects.exclude(assign_status__lte = 2).exclude(cancelled = True).exclude(confirmed = True, confirmed_date__lte = datetime.datetime.now() - datetime.timedelta(days=15)).exclude(public = True).filter(Q(creator=as_user)|Q(pk__in=task_requests.values_list('task', flat = True))|Q(pk__in=task_verification_log.values_list('task', flat = True))).order_by('-pk')

        if request.user.employee.in_staff_group or as_user.employee.GetEmployeeTopParent == as_user:
            context['feedbacks_comment'] = Feedback.objects.filter(feedback_type__needs_verification = True , comment = None)
        else:
            context['feedbacks_comment'] = Feedback.objects.filter(pk = -1)

        if as_user.employee.GetEmployeeTopParent == as_user:
            context['feedbacks_verif'] = Feedback.objects.filter(feedback_type__needs_verification = True , verified = False, rejected = False).exclude( comment = None)
        else:
            context['feedbacks_verif'] = Feedback.objects.filter(pk = -1)

        context['feedbacks_invest'] = Feedback.objects.filter(feedback_type__needs_investigation = True , feedback_type__investigator = request.user , investigated = False)\
            .exclude(feedback_type__needs_verification = True , verified = False)

        context['feedbacks_request'] = Feedback.objects.filter(feedback_type__needs_verification = True , verified = False , rejected = False, requester = request.user)\
            .exclude(id__in = context['feedbacks_comment'].values_list('pk', flat = True))\
                .exclude(id__in = context['feedbacks_verif'].values_list('pk', flat = True))\
                    .exclude(id__in = context['feedbacks_invest'].values_list('pk', flat = True))

        current_task_requests = Task.objects.filter(pk__in = \
            Task_Assign_Request.objects.filter(status=1,user=request.user).exclude(need_verification=True).values_list('task__id', flat=True), confirmed = False).exclude(cancelled = True)

        current_task_requests |= Task.objects.filter(pk__in = \
            Task_Assign_Request.objects.filter(status=1,user__in=request.user.employee.GetAllChildrenUserId).exclude(need_verification=True).values_list('task__id', flat=True), confirmed = False).exclude(cancelled = True)

        current_task_requests |= Task.objects.filter(pk__in = \
            Task_Assign_Request.objects.filter(status=1,task__creator=request.user).exclude(need_verification=True).values_list('task__id', flat=True), confirmed = False).exclude(cancelled = True)


        context['tasks'] = context['tasks'].exclude(pk__in=current_task_requests.values_list('pk', flat=True))

        context["current_task_requests"] = current_task_requests

    
    return render(request, 'Task/request.html', {'context': context})


@login_required(login_url='user:login')
def GetRequestDetail(request, task_id):
    data={}
    try:
        _task = Task.objects.get(pk = task_id)
        requested_users = Task_Assign_Request.objects.filter(task__id = task_id).values_list('user__pk', flat=True)
        verification_users = Task_Verification_Log.objects.filter(task__id = task_id).values_list('verifier__pk', flat=True)
        verification_users_locum = Task_Verification_Log.objects.filter(task__id = task_id).values_list('verifier_locumtenens__pk', flat=True)
        if request.user == _task.creator or request.user.id in requested_users or request.user.id in verification_users or request.user.id in verification_users_locum or (_task.user_assignee and request.user.id in _task.user_assignee.employee.GetEmployeeParentSet) or  (_task.group_assignee and request.user.id in _task.group_assignee.head.employee.GetEmployeeParentSet):
            pass
        else:
            raise PermissionDenied('شما مجاز به دسترسی نیستید')
        serialized = TaskRequestSerializer(_task)
        data["task_request_detail"]=JSONRenderer().render(serialized.data).decode("utf-8") 
    except Exception as err:
        data['message']=err.args[0]
            
    return JsonResponse(data)

@login_required(login_url='user:login') #redirect when user is not logged in
@csrf_exempt
def RejectVerification(request,task_id):
    data={}
    try:
        task_verification_log=Task_Verification_Log.objects.get(Q(task__pk=task_id,verified=None,verifier=request.user)|Q(task__pk=task_id,verified=None,verifier_locumtenens=request.user))
        if task_verification_log and request.method=="POST":
            task_verification_log.verified = False
            task_verification_log.comment = request.body.decode('utf-8')
            task_verification_log.last_verifier = request.user
            task_verification_log.save()
            data['message']="رد درخواست با موفقیت انجام شد"
            data['status']=True
            return JsonResponse(data)
        else:
            data['message']="رد درخواست با خطا مواجه شد"
            data['status']=False
    except Exception as err:
        data['message']="رد درخواست با خطا مواجه شد"
        data['status']=False
    return JsonResponse(data)

@login_required(login_url='user:login') #redirect when user is not logged in
@csrf_exempt
def AcceptVerification(request,task_id):
    data={}
    try:
        task_verification_log=Task_Verification_Log.objects.get(Q(task__pk=task_id,verified=None,verifier=request.user)|Q(task__pk=task_id,verified=None,verifier_locumtenens=request.user))
        if task_verification_log and request.method=="POST":
            task_verification_log.verified = True
            task_verification_log.comment = request.body.decode('utf-8')
            task_verification_log.last_verifier = request.user
            task_verification_log.save()

            if Task_Verification_Log.objects.filter(task=task_verification_log.task,verified=None).count()==0:
                task_assign_request=Task_Assign_Request.objects.filter(task=task_verification_log.task)
                for t in task_assign_request:
                    t.need_verification=False
                    t.save()
            data['message']="تائید درخواست با موفقیت انجام شد"
            data['status']=True
            return JsonResponse(data)
        else:
            data['message']="تائید درخواست با خطا مواجه شد"
            data['status']=False
    except Exception as err:
        data['message']="تائید درخواست با خطا مواجه شد"
        data['status']=False
    return JsonResponse(data)

@login_required(login_url='user:login') #redirect when user is not logged in
@transaction.atomic
def AcceptTaskRequest(request,task_id):
    data={}
    try:
        task_request=Task_Assign_Request.objects.get(task__pk=task_id,user=request.user,status=None)
        if task_request:
            if task_request.notification_status==2:
                data['message']="پذیرش درخواست ممکن نیست"
                return JsonResponse(data)
            with transaction.atomic():
                task_request.status=1
                task_request.save()
                task_requests=Task_Assign_Request.objects.filter(task=task_request.task).exclude(pk=task_request.id)
                if task_requests:
                    for r in task_requests:
                        r.notification_status=2
                        r.save()
                task=Task.objects.get(pk=task_request.task.id)
                task.user_assignee=request.user
                task.assign_status=4    #request accepted
                task.save()
                data['message']="درخواست با موفقیت پذیرفته شد."
        
    except Exception as err:
        data['message']="لطفا دوباره سعی کنید"
    return JsonResponse(data)


@login_required(login_url='user:login') #redirect when user is not logged in
def RejectTaskRequest(request,task_id):
    data={}
    try:
        task_request=Task_Assign_Request.objects.get(task__pk=task_id,user=request.user,status=None)
        if task_request :
            if task_request.notification_status==2:
                data['message']="لطفا دوباره سعی کنید"
                return JsonResponse(data)
            task_request.status=2
            task_request.notification_status=None
            task_request.save()
            
            data['message']="پذیرش درخواست لغو شد."
    except Exception as err:
        data['message']="لطفا دوباره سعی کنید"
    return JsonResponse(data)


@login_required(login_url='user:login') #redirect when user is not logged in
def start(request, task_id):
    try:
        _task = Task.objects.get(id = task_id)
        if _task.user_assignee == request.user and _task.progress == 0 and _task.progress_autocomplete == False and _task.cancelled == False :
            _task.progress = 1
            _task.save()
            return HttpResponse('Success', status = 200)
        else:
            return HttpResponse('Access Denied', status = 403)
    except Exception as ex:
        return HttpResponse(ex.message, status= 400)



@login_required(login_url='user:login') 
def task_detail_panel(request,task_id):
    _user = request.user
    _loc_user = None
    try:
        _loc_user = request.user.locumtenens_organization_groups.first().manager
    except:
        pass
    task=Task.objects.get(pk=task_id)
    if task.user_assignee == _user or task.creator ==_user or (_user.id in task.creator.employee.GetEmployeeParentSet) or (task.user_assignee and _user.id in task.user_assignee.employee.GetEmployeeParentSet)or \
        task.id in request.user.employee.CopyFromAccessTasks or (_loc_user and (task.user_assignee == _loc_user or task.creator==_loc_user or (_loc_user.id in task.creator.employee.GetEmployeeParentSet) or (task.user_assignee and _loc_user.id in task.user_assignee.employee.GetEmployeeParentSet)or \
        task.id in _loc_user.employee.CopyFromAccessTasks) and len(request.user.locumtenens_organization_groups.all())>0 and \
            request.user.locumtenens_organization_groups.first().locumtenens_active) :

        return render(request, 'include/panel/task-detail.html' ,{'task': task})
    else:
        raise PermissionDenied


@login_required(login_url='user:login') 
def request(request):
    return render(request,'task/request/request.html')