from django.shortcuts import render, redirect
from django.http import HttpResponse, Http404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from ...models import Organization_Group,Task_Verification_Log,Task,Task_Level,\
    DashboardCategory,TaskCategory,Task_Assign_Request,Task,Notification,ReportComment,TaskComment,Report,\
        TaskProgress,TaskTime,QualityParameter,QualityOfEmployee, EvaluationLog, FeedbackType, Feedback, MonthStatistic
from django.db.models import Q,FilteredRelation,F,Min,Max,Window,Value,Sum
from django.http import JsonResponse
from ...Serializers.task_management_serializer import Task_Verification_LogSerializer,TaskCommentSerializer,RecentTaskProgressSerializer
from ...Serializers.time_report_serializer import ReportCommentSerializer,ReportSerializer
from django.core import serializers
from rest_framework.renderers import JSONRenderer
from ...utilities.date_tools import ConvertToSolarDate,GetWeekDay,GetPersianMonthName,ConvertToMiladi
import datetime
from datetime import timedelta
from django.db.models.functions.window import FirstValue
from django.db.models import Subquery,OuterRef
import datetime as gdt
from openpyxl import Workbook
from django.core.exceptions import PermissionDenied
from math import ceil
import base64
from urllib.parse import unquote
import jdatetime as jdt


@login_required(login_url='user:login') #redirect when user is not logged in
def kanban(request):

    request.session["activated_menu"]="kanban"
    context={}
    context['dashboard_filters_manager_tasks_checkbox']=False
    try:
        if "dashboard_filters_manager_tasks_checkbox" in request.POST:
            if request.POST['dashboard_filters_manager_tasks_checkbox'] and len(request.user.locumtenens_organization_groups.all())>0 and \
                request.user.locumtenens_organization_groups.first().locumtenens_active:
                as_user = request.user.locumtenens_organization_groups.first().manager
                context['dashboard_filters_manager_tasks_checkbox']=True
            else:
                as_user=request.user
                context['dashboard_filters_manager_tasks_checkbox']=False
        else:
            as_user=request.user
            context['dashboard_filters_manager_tasks_checkbox']=False
    except:
        as_user=request.user
        context['dashboard_filters_manager_tasks_checkbox']=False
    
    try:
        tasks = Task.objects.filter(cancelled=False).filter( Q(creator=as_user)|Q(user_assignee=as_user)|Q(group_assignee__head=as_user)|Q(user_assignee__pk__in=as_user.employee.GetDirectChildrenUserId)|Q(group_assignee__head__pk__in=as_user.employee.GetDirectChildrenUserId))

        parent_tasks = tasks.exclude(task_parent__pk__in=tasks.values_list('pk',flat=True))
        # make task tree
        _tree = ""
        try:
            _tree += "<ul class='time_task_tree'>"
            _tree += "<li class='nodes_time' task_id='0' task_name='همه کارها'> همه کارها </li><hr>"

            for task_node in parent_tasks :
                _tree += "<li  class='nodes_time' type='private' task_name='"+task_node.name.replace("<","&lt;").replace(">","&gt;")+"' task_id=" + \
                    str(task_node.pk)+"><span class='caret_time'>"+task_node.name.replace("<","&lt;").replace(">","&gt;")+"</span><ul class='nested_time'><!--"+str(task_node.pk)+"--></ul></li>"
            for layers in range(10):
                parent_tasks = tasks.filter(task_parent__pk__in=parent_tasks.values_list('pk',flat=True))
                if len(parent_tasks) == 0:
                    break
                else:
                    for task_node in parent_tasks :
                        _tree = _tree.replace("<!--"+str(task_node.task_parent.pk)+"-->" ,"<li  class='nodes_time' type='private' task_name='"+task_node.name.replace("<","&lt;").replace(">","&gt;")+"' task_id=" + \
                            str(task_node.pk)+"><span class='caret_time'>"+task_node.name.replace("<","&lt;").replace(">","&gt;")+"</span><ul class='nested_time'><!--"+str(task_node.pk)+"--><!--"+str(task_node.task_parent.pk)+"--></ul></li>")
            _tree += "</ul>"
        except:
            pass

        context["tree"] = _tree
    except:
        pass
    context['task_level_list'] = Task_Level.objects.all()
    context['dashboard_filters_task_level']=None
    context['dashboard_filters_user_assignee']=None
    context['dashboard_filters_kanban']=request.user.pk
    context['dashboard_filters_task_priority']=None
    context['dashboard_filters_task_key']=None
    context['dashboard_filters_task_name']=None
    context['dashboard_filters_parent_checkbox']=False

    two_weeks_limit = gdt.datetime.now()-gdt.timedelta(days=14)


    if request.method=="POST" and "dashboard_filters_kanban" in request.POST and int(request.POST["dashboard_filters_kanban"])>0 and not int(request.POST["dashboard_filters_kanban"])==request.user.pk and int(request.POST["dashboard_filters_kanban"]) in as_user.employee.GetAllChildrenUserId:
        context['dashboard_filters_kanban']=int(request.POST["dashboard_filters_kanban"])
        as_user=User.objects.get(pk=int(request.POST["dashboard_filters_kanban"]))
        tasks_no_assign=Task.no_assign.filter(creator=as_user).exclude(public=True)
        tasks_no_start=Task.no_start.filter(Q(creator=as_user)|Q(user_assignee=as_user)|Q(group_assignee__head=as_user))
        tasks_start=Task.started.filter(Q(creator=as_user)|Q(user_assignee=as_user)|Q(group_assignee__head=as_user))
        tasks_no_confirmed=Task.no_confirmed.filter(Q(creator=as_user)|Q(user_assignee=as_user)|Q(group_assignee__head=as_user))
        tasks_confirmed=Task.confirmed_tasks.filter(Q(creator=as_user)|Q(user_assignee=as_user)|Q(group_assignee__head=as_user)).filter(updated__gte=two_weeks_limit)
        sub_tasks_no_confirmed=Task.no_confirmed.filter(Q(user_assignee__pk__in=as_user.employee.GetDirectChildrenUserId)|Q(group_assignee__head__pk__in=as_user.employee.GetDirectChildrenUserId)).exclude(Q(creator=as_user)|Q(user_assignee=as_user))
    else:
        tasks_no_assign=Task.no_assign.filter(creator=as_user).exclude(public=True)
        tasks_no_start=Task.no_start.filter(Q(creator=as_user)|Q(user_assignee=as_user)|Q(group_assignee__head=as_user))
        tasks_start=Task.started.filter(Q(creator=as_user)|Q(user_assignee=as_user)|Q(group_assignee__head=as_user))
        tasks_no_confirmed=Task.no_confirmed.filter(Q(creator=as_user)|Q(user_assignee=as_user)|Q(group_assignee__head=as_user))
        tasks_confirmed=Task.confirmed_tasks.filter(Q(creator=as_user)|Q(user_assignee=as_user)|Q(group_assignee__head=as_user)).filter(updated__gte=two_weeks_limit)
        sub_tasks_no_confirmed=Task.no_confirmed.filter(Q(user_assignee__pk__in=as_user.employee.GetDirectChildrenUserId)|Q(group_assignee__head__pk__in=as_user.employee.GetDirectChildrenUserId)).exclude(Q(creator=as_user)|Q(user_assignee=as_user))

    
    #append sub task 
    tasks_no_confirmed |=sub_tasks_no_confirmed
    
    if request.method=="POST":
        context['dashboard_filters_task_level']=int(request.POST["dashboard_filters_task_level"])
        if ("dashboard_filters_user_assignee" in request.POST):
            context['dashboard_filters_user_assignee']=int(request.POST["dashboard_filters_user_assignee"])
        context['dashboard_filters_task_priority']=int(request.POST["dashboard_filters_task_priority"])
        context['dashboard_filters_task_key']=int(request.POST["dashboard_filters_task_key"])
        context['dashboard_filters_task_name']=request.POST["dashboard_filters_task_name"]

        if int(request.POST["dashboard_filters_task_level"])>0:
            tasks_no_assign=tasks_no_assign.filter(task_level__pk=int(request.POST["dashboard_filters_task_level"]))
            tasks_no_start=tasks_no_start.filter(task_level__pk=int(request.POST["dashboard_filters_task_level"]))
            tasks_start=tasks_start.filter(task_level__pk=int(request.POST["dashboard_filters_task_level"]))
            tasks_no_confirmed=tasks_no_confirmed.filter(task_level__pk=int(request.POST["dashboard_filters_task_level"]))
            tasks_confirmed=tasks_confirmed.filter(task_level__pk=int(request.POST["dashboard_filters_task_level"]))
            sub_tasks_no_confirmed=sub_tasks_no_confirmed.filter(task_level__pk=int(request.POST["dashboard_filters_task_level"]))

        if("dashboard_filters_user_assignee" in request.POST and int(request.POST["dashboard_filters_user_assignee"])>0) :
            if "dashboard_filters_kanban" in request.POST and int(request.POST["dashboard_filters_kanban"])>0 and not int(request.POST["dashboard_filters_kanban"])==request.user.pk : 
                pass
            else:
                tasks_no_assign=tasks_no_assign.filter(Q(user_assignee__pk=int(request.POST["dashboard_filters_user_assignee"]))|Q(group_assignee__head__pk=int(request.POST["dashboard_filters_user_assignee"])))
                tasks_no_start=tasks_no_start.filter(Q(user_assignee__pk=int(request.POST["dashboard_filters_user_assignee"]))|Q(group_assignee__head__pk=int(request.POST["dashboard_filters_user_assignee"])))
                tasks_start=tasks_start.filter(Q(user_assignee__pk=int(request.POST["dashboard_filters_user_assignee"]))|Q(group_assignee__head__pk=int(request.POST["dashboard_filters_user_assignee"])))
                tasks_no_confirmed=tasks_no_confirmed.filter(Q(user_assignee__pk=int(request.POST["dashboard_filters_user_assignee"]))|Q(group_assignee__head__pk=int(request.POST["dashboard_filters_user_assignee"])))
                tasks_confirmed=tasks_confirmed.filter(Q(user_assignee__pk=int(request.POST["dashboard_filters_user_assignee"]))|Q(group_assignee__head__pk=int(request.POST["dashboard_filters_user_assignee"])))
                sub_tasks_no_confirmed=sub_tasks_no_confirmed.filter(Q(user_assignee__pk=int(request.POST["dashboard_filters_user_assignee"]))|Q(group_assignee__head__pk=int(request.POST["dashboard_filters_user_assignee"])))

        if "dashboard_filters_parent_checkbox" in request.POST:
            context['dashboard_filters_parent_checkbox']=True
        else:
            context['dashboard_filters_parent_checkbox']=False

        if int(request.POST["dashboard_filters_task_key"])>0:
            task=Task.objects.get(pk=int(request.POST["dashboard_filters_task_key"]))
            tasks_no_assign=tasks_no_assign.filter(Q(pk__in=task.GetAllTaskChildrenId)|Q(pk=int(request.POST["dashboard_filters_task_key"])))
            tasks_no_start=tasks_no_start.filter(Q(pk__in=task.GetAllTaskChildrenId)|Q(pk=int(request.POST["dashboard_filters_task_key"])))
            tasks_start=tasks_start.filter(Q(pk__in=task.GetAllTaskChildrenId)|Q(pk=int(request.POST["dashboard_filters_task_key"])))
            tasks_no_confirmed=tasks_no_confirmed.filter(Q(pk__in=task.GetAllTaskChildrenId)|Q(pk=int(request.POST["dashboard_filters_task_key"])))
            tasks_confirmed=tasks_confirmed.filter(Q(pk__in=task.GetAllTaskChildrenId)|Q(pk=int(request.POST["dashboard_filters_task_key"])))
            # sub_tasks_no_confirmed=sub_tasks_no_confirmed.filter(Q(pk__in=task.GetAllTaskChildrenId)|Q(pk=int(request.POST["dashboard_filters_task_key"])))

        if int(request.POST["dashboard_filters_task_priority"])>0:
            if int(request.POST["dashboard_filters_task_priority"])==1:
                tasks_no_assign=tasks_no_assign.order_by('-task_priority')
                tasks_no_start=tasks_no_start.order_by('-task_priority')
                tasks_start=tasks_start.order_by('-task_priority')
                tasks_no_confirmed=tasks_no_confirmed.order_by('-task_priority')
                tasks_confirmed=tasks_confirmed.order_by('-task_priority')
                # sub_tasks_no_confirmed=sub_tasks_no_confirmed.order_by('-task_priority')
            elif int(request.POST["dashboard_filters_task_priority"])==2:
                tasks_no_assign=tasks_no_assign.order_by('enddate')
                tasks_no_start=tasks_no_start.order_by('enddate')
                tasks_start=tasks_start.order_by('enddate')
                tasks_no_confirmed=tasks_no_confirmed.order_by('enddate')
                tasks_confirmed=tasks_confirmed.order_by('enddate')
                # sub_tasks_no_confirmed=sub_tasks_no_confirmed.order_by('enddate')
            elif int(request.POST["dashboard_filters_task_priority"])==3:
                tasks_no_assign=tasks_no_assign.order_by('-task_level__index')
                tasks_no_start=tasks_no_start.order_by('-task_level__index')
                tasks_start=tasks_start.order_by('-task_level__index')
                tasks_no_confirmed=tasks_no_confirmed.order_by('-task_level__index')
                tasks_confirmed=tasks_confirmed.order_by('-task_level__index')
                # sub_tasks_no_confirmed=sub_tasks_no_confirmed.order_by('-task_level__index')


        if "dashboard_filters_parent_checkbox" not in request.POST:
            # all_task_id=[t.id for t in tasks_no_assign.union(tasks_no_start).union(tasks_start).union(tasks_no_confirmed).union(tasks_confirmed)] #.union(sub_tasks_no_confirmed)
            # all_task_parent_id=[t.task_parent.id if t.task_parent and t.task_parent.id in all_task_id else 0 for t in tasks_no_assign.union(tasks_no_start).union(tasks_start).union(tasks_no_confirmed).union(tasks_confirmed)] #.union(sub_tasks_no_confirmed)
            # all_tasks_children_id=[t.GetAllTaskChildrenId  for t in tasks_no_assign.union(tasks_no_start).union(tasks_start).union(tasks_no_confirmed).union(tasks_confirmed)] #.union(sub_tasks_no_confirmed)
            # all_tasks_children_id=[_id for id_set in all_tasks_children_id for _id in id_set ]
            all_task_id=tasks_no_assign.union(tasks_no_start).union(tasks_start).union(tasks_no_confirmed).union(tasks_confirmed).values_list('id',flat=True) #.union(sub_tasks_no_confirmed)
            all_task_parent_id=tasks_no_assign.union(tasks_no_start).union(tasks_start).union(tasks_no_confirmed).union(tasks_confirmed).values_list('task_parent__id',flat=True) #.union(sub_tasks_no_confirmed)
            all_task_parent_id = list(set(all_task_id) & set(all_task_parent_id))
            # all_tasks_children_id=[t.GetAllTaskChildrenId  for t in tasks_no_assign.union(tasks_no_start).union(tasks_start).union(tasks_no_confirmed).union(tasks_confirmed)] #.union(sub_tasks_no_confirmed)
            # all_tasks_children_id=[_id for id_set in all_tasks_children_id for _id in id_set ]
            all_tasks_children_id = list(set(all_task_id) - set(all_task_parent_id))
            tasks_no_assign=tasks_no_assign.exclude(Q(pk__in=all_task_parent_id)&~Q(pk__in=all_tasks_children_id))
            tasks_no_start=tasks_no_start.exclude(Q(pk__in=all_task_parent_id)&~Q(pk__in=all_tasks_children_id))
            tasks_start=tasks_start.exclude(Q(pk__in=all_task_parent_id)&~Q(pk__in=all_tasks_children_id))
            tasks_no_confirmed=tasks_no_confirmed.exclude(Q(pk__in=all_task_parent_id)&~Q(pk__in=all_tasks_children_id))
            tasks_confirmed=tasks_confirmed.exclude(Q(pk__in=all_task_parent_id)&~Q(pk__in=all_tasks_children_id))
            # sub_tasks_no_confirmed=sub_tasks_no_confirmed.exclude(Q(pk__in=all_task_parent_id)&~Q(pk__in=all_tasks_children_id))

            # tasks_no_assign=tasks_no_assign.exclude(pk__in=[t.id for t in tasks_no_assign.exclude(task_parent__pk__in=all_tasks_id)])    
            # tasks_no_start=tasks_no_start.exclude(pk__in=[t.id for t in tasks_no_start.exclude(task_parent__pk__in=all_tasks_id)])     
            # tasks_start=tasks_start.exclude(pk__in=[t.id for t in tasks_start.exclude(task_parent__pk__in=all_tasks_id)])
            # tasks_no_confirmed=tasks_no_confirmed.exclude(pk__in=[t.id for t in tasks_no_confirmed.exclude(task_parent__pk__in=all_tasks_id)])             
            # tasks_confirmed=tasks_confirmed.exclude(pk__in=[t.id for t in tasks_confirmed.exclude(task_parent__pk__in=all_tasks_id)])   
            # sub_tasks_no_confirmed=sub_tasks_no_confirmed.exclude(pk__in=[t.id for t in sub_tasks_no_confirmed.exclude(task_parent__pk__in=all_tasks_id)])
            
    if request.method=="GET":
        all_task_id=tasks_no_assign.union(tasks_no_start).union(tasks_start).union(tasks_no_confirmed).union(tasks_confirmed).values_list('id',flat=True) #.union(sub_tasks_no_confirmed)
        all_task_parent_id=tasks_no_assign.union(tasks_no_start).union(tasks_start).union(tasks_no_confirmed).union(tasks_confirmed).values_list('task_parent__id',flat=True) #.union(sub_tasks_no_confirmed)
        all_task_parent_id = list(set(all_task_id) & set(all_task_parent_id))
        # all_tasks_children_id=[t.GetAllTaskChildrenId  for t in tasks_no_assign.union(tasks_no_start).union(tasks_start).union(tasks_no_confirmed).union(tasks_confirmed)] #.union(sub_tasks_no_confirmed)
        # all_tasks_children_id=[_id for id_set in all_tasks_children_id for _id in id_set ]
        all_tasks_children_id = list(set(all_task_id) - set(all_task_parent_id))
        tasks_no_assign=tasks_no_assign.exclude(Q(pk__in=all_task_parent_id)&~Q(pk__in=all_tasks_children_id))
        tasks_no_start=tasks_no_start.exclude(Q(pk__in=all_task_parent_id)&~Q(pk__in=all_tasks_children_id))
        tasks_start=tasks_start.exclude(Q(pk__in=all_task_parent_id)&~Q(pk__in=all_tasks_children_id))
        tasks_no_confirmed=tasks_no_confirmed.exclude(Q(pk__in=all_task_parent_id)&~Q(pk__in=all_tasks_children_id))
        tasks_confirmed=tasks_confirmed.exclude(Q(pk__in=all_task_parent_id)&~Q(pk__in=all_tasks_children_id))
    # sub_tasks_no_assign=Task.no_assign.filter(creator__pk__in=as_user.employee.GetDirectChildrenUserId).exclude(creator=as_user) 
    # sub_tasks_no_start=Task.no_start.filter(Q(creator__pk__in=as_user.employee.GetDirectChildrenUserId)|Q(user_assignee__pk__in=as_user.employee.GetDirectChildrenUserId)).exclude(Q(creator=as_user)|Q(user_assignee=as_user))
    # sub_tasks_start=Task.started.filter(Q(creator__pk__in=as_user.employee.GetDirectChildrenUserId)|Q(user_assignee__pk__in=as_user.employee.GetDirectChildrenUserId)).exclude(Q(creator=as_user)|Q(user_assignee=as_user))
    # sub_tasks_no_confirmed=Task.no_confirmed.filter(Q(creator__pk__in=as_user.employee.GetDirectChildrenUserId)|Q(user_assignee__pk__in=as_user.employee.GetDirectChildrenUserId)).exclude(Q(creator=as_user)|Q(user_assignee=as_user))
    # sub_tasks_confirmed=Task.confirmed_tasks.filter(Q(creator__pk__in=as_user.employee.GetDirectChildrenUserId)|Q(user_assignee__pk__in=as_user.employee.GetDirectChildrenUserId)).exclude(Q(creator=as_user)|Q(user_assignee=as_user))
    # sub_tasks_no_assign=Task.no_assign.filter(creator__pk=0).exclude(creator=as_user) 
    # sub_tasks_no_start=Task.no_start.filter(Q(user_assignee__pk__in=as_user.employee.GetDirectChildrenUserId)).exclude(Q(creator=as_user)|Q(user_assignee=as_user))
    # sub_tasks_start=Task.started.filter(Q(user_assignee__pk__in=as_user.employee.GetDirectChildrenUserId)).exclude(Q(creator=as_user)|Q(user_assignee=as_user))
    # sub_tasks_confirmed=Task.confirmed_tasks.filter(Q(user_assignee__pk__in=as_user.employee.GetDirectChildrenUserId)).exclude(Q(creator=as_user)|Q(user_assignee=as_user))

    tasks_no_started_folder=DashboardCategory.objects.filter(user=as_user,column=2)
    context["tasks_no_started_folder"]=tasks_no_started_folder
    tasks_started_folder=DashboardCategory.objects.filter(user=as_user,column=3)
    
    context["tasks_started_folder"]=tasks_started_folder
    tasks_no_confirmed_folder=DashboardCategory.objects.filter(user=as_user,column=4) 
    context["tasks_no_confirmed_folder"]=tasks_no_confirmed_folder


    
    context["tasks_no_assign"]=tasks_no_assign

    context["tasks_no_start_with_folder"]=tasks_no_start.filter(pk__in=TaskCategory.objects.filter(dashboard_category__in=tasks_no_started_folder).values_list('task__id',flat=True))
    context["tasks_no_start_with_no_folder"]=tasks_no_start.exclude(pk__in=TaskCategory.objects.filter(dashboard_category__in=tasks_no_started_folder).values_list('task__id',flat=True))
    
    context["tasks_start_with_folder"]=tasks_start.filter(pk__in=TaskCategory.objects.filter(dashboard_category__in=tasks_started_folder).values_list('task__id',flat=True))
    context["tasks_start_with_no_folder"]=tasks_start.exclude(pk__in=TaskCategory.objects.filter(dashboard_category__in=tasks_started_folder).values_list('task__id',flat=True))

    context["tasks_no_confirmed_with_folder"]=tasks_no_confirmed.filter(pk__in=TaskCategory.objects.filter(dashboard_category__in=tasks_no_confirmed_folder).values_list('task__id',flat=True))
    context["tasks_no_confirmed_with_no_folder"]=tasks_no_confirmed.exclude(pk__in=TaskCategory.objects.filter(dashboard_category__in=tasks_no_confirmed_folder).values_list('task__id',flat=True))

    context["tasks_confirmed"]=tasks_confirmed

    # context["sub_tasks_no_confirmed"]=sub_tasks_no_confirmed
    # context["sub_tasks_no_start"]=[]
    # context["sub_tasks_start"]=[]
    # context["sub_tasks_confirmed"]=[]
    
    context["isManager"]=False

    if(as_user.employee.organization_group.manager==as_user):
        context["isManager"]=True


    context["currentUserIsManager"]=False

    if(request.user.employee.organization_group.manager==request.user):
        context["currentUserIsManager"]=True

    context["isLocuntenens"]=False

    if(len(request.user.locumtenens_organization_groups.all())>0):
        context["isLocuntenens"]=True
    
    try:
        context["children_user"]=User.objects.filter(is_active=True).filter(Q(pk__in=as_user.employee.GetAllChildrenUserId)|Q(pk=as_user.id)).order_by('last_name')
    except:
        pass
    
    try:
        if "dashboard_filters_manager_tasks_checkbox" in request.POST:
            context["children_current_user"]=User.objects.filter(is_active=True).filter(Q(pk__in=as_user.employee.GetAllChildrenUserId)|Q(pk=as_user.id)).order_by('last_name')
        else:
            context["children_current_user"]=User.objects.filter(is_active=True).filter(Q(pk__in=request.user.employee.GetAllChildrenUserId)|Q(pk=request.user.id)).order_by('last_name')
    except:
        pass

    return render(request, 'dashboard/kanban.html', {'context':context})

@login_required(login_url='user:login') #redirect when user is not logged in
def AddCategory(request):
    data={}
    if request.method=="POST":
        try:
            _category=None
            if "category_pk" in request.POST and int(request.POST["category_pk"])>0:
                _category=DashboardCategory.objects.get(pk=int(request.POST["category_pk"]))
                data['FormState']="edit"
            else:
                _category=DashboardCategory()
                data['FormState']="add"

            if _category :
                _category.column=request.POST["column_number"]
                _category.name = request.POST["name"]
                _category.user=request.user
                _category.save()
                data['message']="پوشه جدید با موفقیت ذخیره شد"
                data["status"]=True
                data["id"]=_category.pk
            else:
                data["status"]=False
        
        except Exception as err:
            data['message']=err.args[0]
            data["status"]=False

    return JsonResponse(data)

@login_required(login_url='user:login') #redirect when user is not logged in
def DeleteCategory(request,cat_id):
    data={}
    try:
        _category=DashboardCategory.objects.get(pk=cat_id) 
        data["id"]=_category.pk
        _category.delete()
        data['message']="حذف با موفقیت انجام شد"
        data["status"]=True
    
    except Exception as err:
        data['message']=err.args[0]
        data["status"]=False
    return JsonResponse(data)

@login_required(login_url='user:login') #redirect when user is not logged in
def EditCategory(request,cat_id):
    data={}
    # if request.method=="POST":
    #     try:
    #         _category=DashboardCategory()    
    #         _category.name = request.POST["name"]
    #         _category.user=request.user
    #         _category.save()
    #         data['message']="پوشه جدید با موفقیت ذخیره شد"
    #         data["status"]=True
    #         data["id"]=_category.pk
        
    #     except Exception as err:
    #         data['message']=err.args[0]
    #         data["status"]=False

    return JsonResponse(data)

# function to send all task comments to task profile page
@login_required(login_url='user:login') #redirect when user is not logged in
def SetTaskCategory(request,task_id,category_id):
    data={}
    data["status"]=True
    _task_category=None
    try:
        _task_category=TaskCategory.objects.get(task__id=task_id,dashboard_category__user=request.user)
    except:
        _task_category=None

    try:
        if category_id :
            _task=Task.objects.get(pk=int(task_id))
            _category=DashboardCategory.objects.get(pk=int(category_id))
            if _task_category==None:
                _task_category=TaskCategory()
                _task_category.task=_task
            _task_category.dashboard_category= _category
            _task_category.save()
            data["status"]=True
        else:
            if _task_category:
                _task_category.delete()
                data["status"]=True
        
    except Exception as err:
        data['message']=err.args[0]
        data["status"]=False
    
    return JsonResponse(data)

@login_required(login_url='user:login') #redirect when user is not logged in
def index(request):
    if len(request.user.locumtenens_organization_groups.all())>0 and request.user.locumtenens_organization_groups.first().locumtenens_active:
        as_user = request.user.locumtenens_organization_groups.first().manager
        
    else:
        as_user=request.user

    request.session["activated_menu"]="dashboard"
    context={}
    context["second_date"]=ConvertToSolarDate(datetime.date.today()-timedelta(days=1))
    context["first_date"]=ConvertToSolarDate(datetime.date.today())
    context["second_day"]=GetWeekDay(datetime.date.today()-timedelta(days=1))
    context["first_day"]=GetWeekDay(datetime.date.today())
    
    
    solar_today_list=ConvertToSolarDate(datetime.datetime.now()).split("/")
    context["current_year"]=solar_today_list[0]
    context["current_month"]=solar_today_list[1]

    context["this_persian_month"]=GetPersianMonthName(int(solar_today_list[1]))
    context["prev_month"]=GetPersianMonthName(int(solar_today_list[1])-1)

    context["isManager"]=False
    # task profile user times filter
    _date_time_now=datetime.datetime.now()
    context["dashboard_this_year_range"]=[]
    context["dashboard_this_year_range"].append('سال جاری')
    years=range(int(ConvertToSolarDate(_date_time_now).split("/")[0])-1 ,int(ConvertToSolarDate(_date_time_now).split("/")[0])-10 ,-1)
    for i in years:
        context["dashboard_this_year_range"].append(i)
    try:
        selected_user_id = abs(int(request.GET.get("u_id","")))
        if selected_user_id in as_user.employee.GetAllChildrenUserId or selected_user_id == as_user.id:
            pass
        else:
            raise PermissionDenied
        if selected_user_id == 0:
            selected_user_id = request.user.id
    except:
        selected_user_id = request.user.id
    try:
        selected_year = abs(int(request.GET.get("year","")))
    except:
        selected_year = int( ConvertToSolarDate(datetime.datetime.now()).split("/")[0] )
    try:
        selected_month = abs(int(request.GET.get("month","")))
    except:
        selected_month = int( ConvertToSolarDate(datetime.datetime.now()).split("/")[1] )

    context["selected_user_id"] = selected_user_id
    context["dashboard_this_year"] = selected_year 
    context["dashboard_this_month"] = selected_month

    stat_year = selected_year if selected_month > 1 else (selected_year - 1)
    stat_month = (selected_month -1) if selected_month > 1 else 12
    
    if MonthStatistic.objects.filter(user_id = selected_user_id, year = stat_year, month = stat_month).exists():
        context["month_stat"] = MonthStatistic.objects.get(user_id = selected_user_id, year = stat_year, month = stat_month)
    else:
        context["month_stat"] = None

    
    if(as_user.employee.organization_group.manager==as_user):
        context["isManager"]=True

    context["isLocuntenens"]=False

    if(len(request.user.locumtenens_organization_groups.all())>0):
        context["isLocuntenens"]=True

    context["isDirectManager"] = False
    if selected_user_id  in request.user.employee.GetDirectChildrenUserId:
        context["isDirectManager"] = True

    try:
        if request.user.employee.in_staff_group :
            context["children_user"]=User.objects.filter(is_active=True).order_by('last_name')
        else:
            context["children_user"]=User.objects.filter(is_active=True).filter(Q(pk__in=as_user.employee.GetAllChildrenUserId)|Q(pk=as_user.id)).order_by('last_name')
    except:
        pass
    
    context["feedback_type"] = FeedbackType.objects.all()

    context["feedback"] = Feedback.objects.filter(user__id = selected_user_id)[0:20]

    context["evaluation_log"] = EvaluationLog.objects.filter(evaluatee__id = selected_user_id, evaluator__id = request.user.id).order_by("-updated")[:50]

    context["pos_feedback"]= None
    context["neg_feedback"]= None

    if Feedback.objects.filter(user__id = selected_user_id, seen = False).exists() and selected_user_id == request.user.id:
        _feedback = Feedback.objects.filter(user__id = selected_user_id, seen = False).exclude(verified = False, feedback_type__needs_verification = True).first()
        if _feedback and _feedback.feedback_type.pos_or_neg :
            context["pos_feedback"]= _feedback
        else:
            context["neg_feedback"]= _feedback

    return render(request, 'dashboard/index.html', {'context':context})

@login_required(login_url='user:login') #redirect when user is not logged in
def GetLastComments(request):
    data={}
    try:
        last_two_week=datetime.date.today()-timedelta(days=14)

        report_comment=ReportCommentSerializer(ReportComment.objects.filter(report__task_time__user=request.user,created__gte=last_two_week).order_by('-created') , many=True)
        data["report_comment"]=JSONRenderer().render(report_comment.data).decode("utf-8")

        task_comment=TaskCommentSerializer(TaskComment.objects.filter(task__user_assignee=request.user,created__gte=last_two_week).order_by('-created') , many=True)
        data["task_comment"]=JSONRenderer().render(task_comment.data).decode("utf-8")

        data['status']=True
        
    except Exception as err:
        data['message']="فراخوانی کامنت های اخیر با خطا مواجه شد"
        data['status']=False
    return JsonResponse(data)
    
@login_required(login_url='user:login') #redirect when user is not logged in
def GetLastReports(request):
    data={}
    try:
        last_date_for_show = datetime.datetime.now() - datetime.timedelta(days=30) 

        no_confirm_report = Report.objects.filter(task_time__start__gte = last_date_for_show ).filter(Q(task_time__user__pk__in=request.user.employee.GetDirectChildrenUserId) | Q(task_time__user=request.user),confirmed=False).order_by('-task_time__start')[:10]
        confirmed_report = Report.objects.filter(task_time__start__gte = last_date_for_show ).filter(Q(task_time__user__pk__in=request.user.employee.GetDirectChildrenUserId) | Q(task_time__user=request.user),confirmed=True).order_by('-task_time__start')[:10]
        
        # all_recent_report=confirmed_report.union(no_confirm_report)
        #.order_by('confirmed','-task_time__start') 
        reports=ReportSerializer(no_confirm_report, many=True)
        data["no_confirm_report"]=JSONRenderer().render(reports.data).decode("utf-8")
        reports=ReportSerializer(confirmed_report, many=True)
        data["confirmed_report"]=JSONRenderer().render(reports.data).decode("utf-8")
        data['status']=True
        
    except Exception as err:
        data['message']="فراخوانی گزارش های اخیر با خطا مواجه شد"
        data['status']=False
    return JsonResponse(data)

@login_required(login_url='user:login') #redirect when user is not logged in
def GetRecentTaskProgress(request):
    data={}
    try:
        last_week=datetime.date.today()-timedelta(days=7)

        tasks=Task.objects.filter(cancelled=False,pk__in=TaskProgress.objects.filter(progress_date__gte= last_week).values('task__id'))\
            .filter( Q(user_assignee=request.user)|Q(group_assignee__head=request.user)|Q(user_assignee__pk__in=request.user.employee.GetDirectChildrenUserId)|Q(group_assignee__head__pk__in=request.user.employee.GetDirectChildrenUserId)).values('id','name','created',)\
                .annotate(progress1=Subquery(TaskProgress.objects.filter(task__id=OuterRef('pk'),).order_by('-id').values('progress_value')[:1]))\
                    .annotate(progress2=Subquery(TaskProgress.objects.filter(task__id=OuterRef('pk'),).order_by('-id').values('progress_value')[1:2]))\
                        .annotate(date1=Subquery(TaskProgress.objects.filter(task__id=OuterRef('pk'),).order_by('-id').values('progress_date')[:1]))\
                            .annotate(date2=Subquery(TaskProgress.objects.filter(task__id=OuterRef('pk'),).order_by('-id').values('progress_date')[1:2])).order_by('-date1')
        task_serialize=RecentTaskProgressSerializer(tasks, many=True)
        data["tasks"]=JSONRenderer().render(task_serialize.data).decode("utf-8")
        data['status']=True
        
    except Exception as err:
        data['message']="فراخوانی گزارش های تائید نشده با خطا مواجه شد"
        data['status']=False
    return JsonResponse(data)

@login_required(login_url='user:login') #redirect when user is not logged in
def GetRecentTaskCollaburation(request, user_id, year, month):
    if len(request.user.locumtenens_organization_groups.all())>0 and request.user.locumtenens_organization_groups.first().locumtenens_active:
        as_user = request.user.locumtenens_organization_groups.first().manager
        
    else:
        as_user=request.user
    _user=None
    if user_id:
        _user=user_id
    else:
        _user=request.user.id

    if year != 0:
        year = int(year)
    else:
        year = int(ConvertToSolarDate(datetime.datetime.now()).split("/")[0])

    if month != 0:
        month = int(month)
    else:
        month = int(ConvertToSolarDate(datetime.datetime.now()).split("/")[1])

    this_user=User.objects.get(pk=_user)
    if as_user.id != this_user.id and as_user.id not in this_user.employee.GetEmployeeParentSet:
        raise PermissionDenied

    data={}
    try:
        solar_today_list=ConvertToSolarDate(datetime.datetime.now()).split("/")
        _first_date_time_in_month=datetime.datetime.strptime(ConvertToMiladi(str(year)+"/"+str(month)+"/1")+" 00:00:00",'%Y-%m-%d %H:%M:%S')
        _last_date_time_in_month=datetime.datetime.strptime(ConvertToMiladi(str(year)+"/"+str(month)+"/1")+" 23:59:59",'%Y-%m-%d %H:%M:%S')
        for i in range(2,32):
            _last_date_time_in_month += datetime.timedelta(days=1)
            if str(ConvertToSolarDate(_last_date_time_in_month).split("/")[1]) != str(month):
                _last_date_time_in_month -= datetime.timedelta(days=1)
        
        task_time=TaskTime.objects.filter(user=this_user,start__gte=_first_date_time_in_month,end__lte=_last_date_time_in_month).annotate(time_diff=F('end')-F('start')).values('task__name','time_diff','task__id')

        tasks_list={}
        sum_times=datetime.timedelta() 
        for t in task_time:
            sum_times+=t["time_diff"]
            if t["task__name"] in tasks_list.keys():
                tasks_list[t["task__name"]]=tasks_list[t["task__name"]]+t["time_diff"]
            else:
                tasks_list[t["task__name"]]=t["time_diff"]
        
        tasks_list=dict(sorted(tasks_list.items(),key=lambda item:item[1],reverse=True))

        for t in tasks_list.keys():
            _task_time_percent=tasks_list[t]*100/sum_times
            for j in task_time:
                if t == j['task__name']:
                    t_id = j['task__id']
            tasks_list[t]=[tasks_list[t],_task_time_percent , t_id]
        
        
        data["tasks_list"]=tasks_list
        data['status']=True
        
    except Exception as err:
        data['message']="فراخوانی مشارکت در کارها با خطا مواجه شد"
        data['status']=False
    return JsonResponse(data)

@login_required(login_url='user:login') #redirect when user is not logged in
def ExportUserTaskTimes(request):
    if len(request.user.locumtenens_organization_groups.all())>0 and request.user.locumtenens_organization_groups.first().locumtenens_active:
        as_user = request.user.locumtenens_organization_groups.first().manager
        
    else:
        as_user=request.user

    try:
        if request.method == "POST":
            if "dashboard_task_time_list_user_id" in request.POST:
                user_id = int( request.POST["dashboard_task_time_list_user_id"] )

            if "dashboard_task_time_list_year" in request.POST:
                year = int( request.POST["dashboard_task_time_list_year"] )
 
            if "dashboard_task_time_list_month" in request.POST:
                month = int( request.POST["dashboard_task_time_list_month"] ) 
    except Exception as ex:
        response=HttpResponse("عملیات با خطا مواجه شد")

    if user_id:
        _user = User.objects.get(pk=user_id)
    else:
        _user = request.user

    if year != 0:
        year = int(year)
    else:
        year = int(ConvertToSolarDate(datetime.datetime.now()).split("/")[0])
    if month != 0:
        month = int(month)
    else:
        month = int(ConvertToSolarDate(datetime.datetime.now()).split("/")[1])


    # to find first time and last time in current month
    _first_date_time_in_month=datetime.datetime.strptime(ConvertToMiladi(str(year)+"/"+str(month)+"/1")+" 00:00:00",'%Y-%m-%d %H:%M:%S')
    _last_date_time_in_month=datetime.datetime.strptime(ConvertToMiladi(str(year)+"/"+str(month)+"/1")+" 23:59:59",'%Y-%m-%d %H:%M:%S')
    for i in range(2,32):
        _last_date_time_in_month += datetime.timedelta(days=1)
        if str(ConvertToSolarDate(_last_date_time_in_month).split("/")[1]) != str(month):
            _last_date_time_in_month -= datetime.timedelta(days=1)

    if as_user.id not in _user.employee.GetEmployeeParentSet and as_user.id != _user.id:
        raise PermissionDenied

    # user_tasks = Task.objects.filter(user_assignee__pk = _user.id).exclude(confirmed_date__lte = _first_date_time_in_month).exclude(startdate__gte = _last_date_time_in_month)
    task_times = TaskTime.objects.filter(user=_user ,start__gte=_first_date_time_in_month,end__lte=_last_date_time_in_month) # , task__user_assignee = _user 
    user_tasks = []
    all_time = 0
    for j in task_times:
        all_time += (j.end - j.start).seconds
        if j.task in user_tasks:
            pass
        else:
            user_tasks.append(j.task)

    try:
        # creat excell 
        task_list = []

        # excel headers
        excel_title=["ردیف" , "عنوان فعالیت" , "ساعت" ,"درصد", "شروع" ,  "پایان" , "درصد ماه گذشته" , "درصد ماه جاری" ,  "نتایج و رویدادها" ]
        task_list.append(excel_title)

        for i in range(len(user_tasks)):
            task = user_tasks[i]
            t_row = i + 1
            t_name = task.name

            # task progress changes
            if task.current == False:

                task_progress_data={}
                try:
                    task_time_progress = TaskProgress.objects.filter(task=task)
                    for i in task_time_progress:
                        _date = i.progress_date   # changes date
                        task_progress_data[_date] = i.progress_value  #changes value

                    # task_progress_all_data contains all points in chart
                    task_progress_all_data = []

                    progress_first_day = task_time_progress[0].progress_date      # first change date 
                    progress_last_day = task_time_progress[len(task_time_progress)-1].progress_date   # last change date

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
                        current_value = task_progress_data[progress_first_day]  
                    for i in progress_days:
                        if i in task_progress_data:          # when point exist in database
                            current_value =  task_progress_data[i]
                            task_progress_all_data.append([i.date() , current_value ]) 
                            current_day = i.date()
                        else:
                            task_progress_all_data.append([i.date() , current_value ])   # when point dosn't exist in data base we make last change as this point change
                            current_day = i.date()
                
                except:
                    pass



                # For calculate previous month percent and current month percent 
                if len(task_progress_all_data)>0:
                    task_procress_first_record = task_progress_all_data[0]
                    task_procress_last_record = task_progress_all_data[len(task_progress_all_data)-1]
                    _last_date_time_in_previous_month = _first_date_time_in_month - timedelta(seconds=60)

                    previous_val = 0
                    current_Val = 0
                    LP = _last_date_time_in_previous_month.date()
                    LC= _last_date_time_in_month.date() 
                    A = task_procress_first_record
                    B = task_procress_last_record

                
                    if B[0] < LP: #1
                        previous_val = B[1]
                        current_Val = B[1]

                    elif A[0] < LP and B[0] < LC : #2
                        for k in task_progress_all_data:
                            if k[0] == LP:
                                previous_val = k[1]
                        current_Val = B[1]

                    elif A[0] < LP and B[0] > LC : #3
                        for k in task_progress_all_data:
                            if k[0] == LP:
                                previous_val = k[1]
                        for k in task_progress_all_data:
                            if k[0] == LC:
                                current_Val = k[1]                            

                    elif A[0] > LP and B[0] < LC :#4
                        previous_val = 0
                        current_Val = B[1]

                    elif A[0] > LP and B[0] > LC :#5
                        previous_val = 0
                        for k in task_progress_all_data:
                            if k[0] == LC:
                                current_Val = k[1]                       

                    elif A[0] >LC :#6
                        previous_val = 0
                        current_Val = 0
                else:
                    previous_val = 0
                    current_Val = 0
                t_last_month_percent = str(previous_val)
                t_current_month_percent = str(current_Val)   
            else:
                previous_val = "جاری"
                current_Val = "جاری"     
                t_last_month_percent = str(previous_val)
                t_current_month_percent = str(current_Val)   
 
            this_task_times = TaskTime.objects.filter(user=_user , task__user_assignee = _user ,start__gte=_first_date_time_in_month,end__lte=_last_date_time_in_month,task = task)
            t_time = 0
            for j in this_task_times:
                t_time += (j.end - j.start).seconds
            if all_time != 0 :
                t_time_percent = round((t_time / all_time) * 100 ,2)
            else:
                t_time_percent = 0

            t_start = ConvertToSolarDate(task.startdate)
            t_end = ConvertToSolarDate(task.enddate)  

            task_reports = Report.objects.filter(task_time__user=_user,task_time__start__gte=_first_date_time_in_month,task_time__end__lte=_last_date_time_in_month,task_time__task = task )
            task_events = 0
            task_results = 0

            t_over_time_reports_number = 0
            for j in task_reports:
                if j.report_type == 2:
                    task_events += 1
                if j.report_type == 3:
                    task_results += 1 
                if task.enddate:
                    if j.task_time.start.date() > task.enddate:
                        t_over_time_reports_number += 1

            t_result_event = "  " + str(task_events) + "  " + " رویداد " + "  " + str(task_results) + "  " + " نتیجه " + "  " + str(t_over_time_reports_number) + "  " + "گزارش خارج از بازه زمانی"


            task_record = [t_row , t_name , t_time ,t_time_percent , t_start , t_end, t_last_month_percent, t_current_month_percent,t_result_event]
            if task.user_assignee == _user:
                task_list.append(task_record)
            else:
                pass
                    
        wb = Workbook()
        sheet = wb.active
        sheet.title = "کارها"
        sheet.column_dimensions["A"].width = 5
        sheet.column_dimensions["B"].width = 40
        sheet.column_dimensions["C"].width = 10
        sheet.column_dimensions["D"].width = 10
        sheet.column_dimensions["E"].width = 15
        sheet.column_dimensions["F"].width = 15
        sheet.column_dimensions["G"].width = 15
        sheet.column_dimensions["H"].width = 15
        sheet.column_dimensions["I"].width = 40
        sheet.sheet_view.rightToLeft = True

        m = 0
        for i in task_list:
            m += 1
            n=0
            for j in i:
                n += 1
                a = sheet.cell (row=m , column=n ) 
                a.value = j


        response = HttpResponse( content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" , )
        response["Content-Disposition"] = "attachment;filename=task-{date}.xlsx".format(date = datetime.datetime.now().strftime("%Y-%m-%d"),)

        wb.save(response)

    except Exception as ex:
        response=HttpResponse("عملیات با خطا مواجه شد")
    return  response


@login_required(login_url='user:login') #redirect when user is not logged in
def RegisterEmployeeQuality(request):
    try:
        user_id = abs(int(request.GET.get("u_id","")))
        if user_id == 0:
            user_id = request.user.id
    except:
        user_id = request.user.id
    try:
        year = abs(int(request.GET.get("year","")))
        if year == 0:
            year = int( ConvertToSolarDate(datetime.datetime.now()).split("/")[0] )
    except:
        year = int( ConvertToSolarDate(datetime.datetime.now()).split("/")[0] )
    try:
        month = abs(int(request.GET.get("month","")))
        if month == 0:
            month = int( ConvertToSolarDate(datetime.datetime.now()).split("/")[1] )
    except:
        month = int( ConvertToSolarDate(datetime.datetime.now()).split("/")[1] )

    try:
        user = User.objects.get(id=user_id)
    except:
        user = request.user  
    context = {}
    current_user = request.user
    if user_id not in current_user.employee.GetDirectChildrenUserId:
        raise PermissionDenied
    all_weight = 0
    all_score = 0
    score={}
    try:
        parameters = QualityParameter.objects.filter(group=current_user.employee.organization_group)
        parameters_name=[]
        for i in parameters:
            parameter_id = "quality_parameter_"+str(i.id)
            all_weight += i.weight
            if parameter_id in request.POST:
                score[parameter_id] = int(request.POST[parameter_id])
                quality= QualityOfEmployee.objects.filter(year=year, month=month, user=user).filter(parameter__id=i.id)
                if quality:
                    try:
                        if int(request.POST[parameter_id]) <=100 and int(request.POST[parameter_id])>=0:
                            quality[0].value = int(request.POST[parameter_id])
                            all_score += int(request.POST[parameter_id]) * i.weight
                        else:
                            quality[0].value = 0
                            all_score += 0
                    except:
                           quality[0].value = 0
                           all_score += 0
                    quality[0].save() 
                else:
                    quality = QualityOfEmployee()
                    quality.parameter = i
                    quality.year = year
                    quality.month = month
                    quality.user = User.objects.get(id = user_id)
                    try:
                        if int(request.POST[parameter_id]) <=100 and int(request.POST[parameter_id])>=0:
                            quality.value = int(request.POST[parameter_id])
                            all_score += int(request.POST[parameter_id]) * i.weight
                        else:
                            quality.value = 0
                            all_score += 0
                    except:
                        quality.value = 0
                        all_score += 0

                    quality.save() 

        context["message"] = "حق کیفیت ثبت شد"
        context["status"] = True
        context["score"] = score
        if all_weight != 0:
            context["value"]=int(all_score/all_weight) 
        else:
            context["value"]= 0
    except Exception as ex:
        context["message"] = ex.args[0] # "بروز خطا"
        context["status"] = False
        context["value"]= 0
    return  JsonResponse(context)

@login_required(login_url='user:login') #redirect when user is not logged in
def ShowEmployeeQuality(request):
    if len(request.user.locumtenens_organization_groups.all())>0 and request.user.locumtenens_organization_groups.first().locumtenens_active:
        as_user = request.user.locumtenens_organization_groups.first().manager
        
    else:
        as_user=request.user
    try:
        user_id = abs(int(request.GET.get("u_id","")))
        if user_id == 0:
            user_id = request.user.id
    except:
        user_id = request.user.id
    try:
        year = abs(int(request.GET.get("year","")))
        if year == 0:
            year = int( ConvertToSolarDate(datetime.datetime.now()).split("/")[0] )
    except:
        year = int( ConvertToSolarDate(datetime.datetime.now()).split("/")[0] )
    try:
        month = abs(int(request.GET.get("month","")))
        if month == 0:
            month = int( ConvertToSolarDate(datetime.datetime.now()).split("/")[1] )
    except:
        month = int( ConvertToSolarDate(datetime.datetime.now()).split("/")[1] )

    try:
        selected_user = User.objects.get(id=user_id)
    except:
        selected_user = request.user
    context = {}
    score={}

    
    if user_id not in as_user.employee.GetAllChildrenUserId and as_user != selected_user:
        raise PermissionDenied
    try:
        if selected_user.employee.IsManager:
            selected_user_parent = User.objects.get(id = selected_user.employee.GetEmployeeParent)
            parameters = QualityParameter.objects.filter(group=selected_user_parent.employee.organization_group)
        else:
            parameters = QualityParameter.objects.filter(group=selected_user.employee.organization_group)


        parameters_name=[]
        for i in parameters:
            parameter_id = "quality_parameter_"+str(i.id)
            try:
                score[parameter_id] = [i.id , i.name , i.weight , QualityOfEmployee.objects.get(month=month , year = year , user =selected_user , parameter=i).value ]
            except:
                score[parameter_id] = [i.id , i.name , i.weight , 0]
    except:
        pass
    context["score"]=score
    context["isDirectManager"] = None
    if user_id  in request.user.employee.GetDirectChildrenUserId:
        context["isDirectManager"] = 1

    return  JsonResponse(context)

@login_required(login_url='user:login') #redirect when user is not logged in
def GetCurrentMonthEmployeeQuality(request,user_id, year, month):
    if len(request.user.locumtenens_organization_groups.all())>0 and request.user.locumtenens_organization_groups.first().locumtenens_active:
        as_user = request.user.locumtenens_organization_groups.first().manager
        
    else:
        as_user=request.user
    _user=None
    if user_id:
        _user=user_id
    else:
        _user=request.user.id

    if year != 0:
        year = int(year)
    else:
        year = int(ConvertToSolarDate(datetime.datetime.now()).split("/")[0])

    if month != 0:
        month = int(month)
    else:
        month = int(ConvertToSolarDate(datetime.datetime.now()).split("/")[1])

    this_user=User.objects.get(pk=_user)
    if _user !=as_user.id and as_user.id not in this_user.employee.GetEmployeeParentSet:
        raise PermissionDenied
    
    if month == 1:
        prev_month = 12
        prev_year = year - 1
    else:
        prev_month = month -1
        prev_year = year

    context={}
    try:
        current_quality = QualityOfEmployee.objects.filter(user = this_user, year = year, month = month)
        prev_quality = QualityOfEmployee.objects.filter(user = this_user, year = prev_year, month = prev_month)

        all_weight = 0
        all_score=0
        for i in current_quality:
            all_score += i.parameter.weight * i.value
            all_weight += i.parameter.weight 
        if all_weight > 0 and all_score > 0:
            context["current_quality"]= int(ceil(all_score /all_weight , 0))
        else:
            context["current_quality"]= 0

        all_weight = 0
        all_score=0
        for i in prev_quality:
            all_score += i.parameter.weight * i.value
            all_weight += i.parameter.weight 
        if all_weight > 0 and all_score > 0:
            context["prev_quality"]= int(ceil(all_score /all_weight , 0))
        else:
            context["prev_quality"]= 0            
    except:
        pass
    return  JsonResponse(context)

@login_required(login_url='user:login')
def AddFeedback(request):
    if len(request.user.locumtenens_organization_groups.all())>0 and request.user.locumtenens_organization_groups.first().locumtenens_active:
        as_user = request.user.locumtenens_organization_groups.first().manager
        
    else:
        as_user=request.user

    try:
        user_id = abs(int(request.POST.get('add_feedback_user_input','0')))
        if user_id == 0:
            user_id = request.user.id
    except:
        user_id = request.user.id
    
    try:
        selected_user = User.objects.get(id=user_id)
    except:
        selected_user = request.user

    if user_id not in as_user.employee.GetAllChildrenUserId and as_user != selected_user and request.user.employee.in_staff_group == False:
        raise PermissionDenied

    try:
        _feedback = Feedback()
        _feedback.feedback_type = FeedbackType.objects.get(pk = abs(int(request.POST.get('add_feedback_type_input','0'))))
        _feedback.user = selected_user
        _feedback.requester = request.user
        _feedback.title = request.POST.get('add_feedback_title_input','')
        if _feedback.feedback_type.has_value :
            _feedback.value = abs(int(request.POST.get('add_feedback_value_input','0')))
        _feedback.description = request.POST.get('add_feedback_desc_input','')

        _feedback.save()

        for key in request.POST.keys():
            if key.find('add_feedback_log_input_') >= 0:
                log_id = int(key.replace('add_feedback_log_input_',''))
                log_value = (request.POST[key] == 'on')
                _log = EvaluationLog.objects.get(pk = log_id , evaluator = request.user, evaluatee = selected_user)
                _feedback.logs.add(_log)

        _feedback.save()

    except:
        pass

    return redirect(request.GET.get('next','/'))

@login_required(login_url='user:login')
def CommentFeedback(request, feedback_id):
    if request.user.employee.in_staff_group:
        try:
            comment = request.body.decode()
            _feedback = Feedback.objects.get(pk = feedback_id)
            _feedback.comment = comment
            _feedback.save()
            return JsonResponse('OK', safe = False)
        except:
            return JsonResponse('Fail', safe = False)
    else:
        raise PermissionDenied

@login_required(login_url='user:login')
def VerifyFeedback(request, feedback_id):
    if len(request.user.locumtenens_organization_groups.all())>0 and request.user.locumtenens_organization_groups.first().locumtenens_active:
        as_user = request.user.locumtenens_organization_groups.first().manager
        
    else:
        as_user=request.user

    if as_user.employee.GetEmployeeTopParent == as_user:
        try:
            _feedback = Feedback.objects.get(pk = feedback_id)
            if _feedback.comment == None:
                return JsonResponse('Fail', safe = False)
            _feedback.verified = True
            _feedback.ver_rej_date = gdt.datetime.now()
            _feedback.save()
            return JsonResponse('OK', safe = False)
        except:
            return JsonResponse('Fail', safe = False)
    else:
        raise PermissionDenied

@login_required(login_url='user:login')
def RejectFeedback(request, feedback_id):
    if len(request.user.locumtenens_organization_groups.all())>0 and request.user.locumtenens_organization_groups.first().locumtenens_active:
        as_user = request.user.locumtenens_organization_groups.first().manager
        
    else:
        as_user=request.user

    if as_user.employee.GetEmployeeTopParent == as_user:
        try:
            _feedback = Feedback.objects.get(pk = feedback_id)
            if _feedback.comment == None:
                return JsonResponse('Fail', safe = False)
            _feedback.rejected = True
            _feedback.ver_rej_date = gdt.datetime.now()
            _feedback.save()
            return JsonResponse('OK', safe = False)
        except:
            return JsonResponse('Fail', safe = False)
    else:
        raise PermissionDenied

@login_required(login_url='user:login')
def InvestigateFeedback(request, feedback_id):
    try:
        _feedback = Feedback.objects.get(pk = feedback_id)
        comment = request.body.decode()
        if (_feedback.verified == False) or (_feedback.feedback_type.investigator != request.user):
            return JsonResponse('Fail', safe = False)
        _feedback.investigated = True
        _feedback.invest_date = gdt.datetime.now()
        _feedback.investigation_comment = comment
        _feedback.save()
        return JsonResponse('OK', safe = False)
    except:
        return JsonResponse('Fail', safe = False)

@login_required(login_url='user:login')
def SeeFeedback(request, feedback_id):
    try:
        _feedback = Feedback.objects.get(pk = feedback_id)
        if (_feedback.user != request.user):
            return JsonResponse('Fail', safe = False)
        _feedback.seen = True
        _feedback.save()
        return JsonResponse('OK', safe = False)
    except:
        return JsonResponse('Fail', safe = False)

@login_required(login_url='user:login')
def DeleteFeedback(request, feedback_id):
    try:
        _feedback = Feedback.objects.get(pk = feedback_id)
        if _feedback.verified or _feedback.comment or _feedback.investigated  or (_feedback.requester != request.user):
            return JsonResponse('Fail', safe = False)
        _feedback.delete()
        return JsonResponse('OK', safe = False)
    except:
        return JsonResponse('Fail', safe = False)

@login_required(login_url='user:login')
def EditFeedback(request, feedback_id):
    try:
        _feedback = Feedback.objects.get(pk = feedback_id)
        if _feedback.verified or _feedback.comment or _feedback.investigated  or (_feedback.requester != request.user):
            return JsonResponse('Fail', safe = False)
        if request.method=="POST" and 'request_page_feedback_title' in request.POST and 'request_page_feedback_description' in request.POST :
            _feedback.title = request.POST['request_page_feedback_title']
            _feedback.description = request.POST['request_page_feedback_description']
            _feedback.save()
            return JsonResponse('OK', safe = False)
        else:
            return JsonResponse('Fail', safe = False)
    except:
        return JsonResponse('Fail', safe = False)


@login_required(login_url='user:login') 
def dashboard(request):
    if request.user.employee.IsManager:
        return index(request)
    else:    
        context = {}

        tasks = Task.objects.filter(cancelled=False).filter(user_assignee=request.user)

        current_tasks = tasks.filter(current = True)
        todo_tasks = tasks.filter(progress = 0, current = False)
        doing_tasks = tasks.filter(progress__gt = 0, progress__lt = 100, current = False)

        context["current_tasks"] = current_tasks
        context["todo_tasks"] = todo_tasks
        context["doing_tasks"] = doing_tasks

        return render(request, 'dashboard/dashboard-employee.html', {'context':context})

@login_required(login_url='user:login') 
def kanban_current(request):
    context = {}
    tasks = Task.objects.filter(cancelled=False).filter(user_assignee=request.user)
    current_tasks = tasks.filter(current = True)
    return render(request, 'dashboard/widget/kanban-current.html', {'current_tasks':current_tasks})


@login_required(login_url='user:login') 
def kanban_todo(request):
    context = {}
    tasks = Task.objects.filter(cancelled=False).filter(user_assignee=request.user)
    todo_tasks = tasks.filter(progress = 0, current = False)
    return render(request, 'dashboard/widget/kanban-todo.html', {'todo_tasks':todo_tasks})


@login_required(login_url='user:login') 
def kanban_doing(request):
    context = {}
    tasks = Task.objects.filter(cancelled=False).filter(user_assignee=request.user)
    doing_tasks = tasks.filter(progress__gt = 0, progress__lt = 100, current = False)
    return render(request, 'dashboard/widget/kanban-doing.html', {'doing_tasks':doing_tasks})


@login_required(login_url='user:login') 
def dashboard_calendar(request,month_diff):
    month_diff = int(month_diff)
    days_info = []
    year = jdt.date.today().year
    month = jdt.date.today().month + month_diff
    while month > 12:
        year += 1
        month -= 12
    while month < 1:
        year -= 1
        month += 12

    month_name = jdt.date.j_months_fa[month-1]
    month_name += " " + str(year)

    first_day = jdt.date(year=year,month=month,day=1)
    try:
        jdt.date(year=year,month=month,day=31)
        month_len = 31
    except:
        try:
            jdt.date(year=year,month=month,day=30)
            month_len = 30
        except:
            jdt.date(year=year,month=month,day=29)
            month_len = 29

    for i in range(month_len):
        day_index = i+1
        day_info={}
        day = jdt.date(year=year,month=month,day=day_index)
        if day == jdt.date.today():
            day_info["today"] = True
        else:
            day_info["today"] = False
        day_info["weekday"] = day.weekday()
        days_info.append(day_info)

    return render(request, 'include/widget/calendar.html', {'days_info':days_info, \
        'month_name':month_name, 'prev_month_diff':month_diff - 1, 'next_month_diff':month_diff + 1})
