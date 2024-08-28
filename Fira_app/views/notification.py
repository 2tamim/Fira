from django.db import transaction
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from ..models import Task_Assign_Request,Task,Notification,SystemSetting,TaskTime,Report,Task_Verification_Log,Feedback\
    ,Organization_Group
from django.db.models import Q,FilteredRelation,F,Min,Max,Window,Value,Sum
from django.http import JsonResponse
from ..Serializers.task_management_serializer import Task_Assign_RequestSerializer
from django.core import serializers
from rest_framework.renderers import JSONRenderer
import datetime

@login_required(login_url='user:login') #redirect when user is not logged in
def GetNotificationNumber(request):
    data={}
    system_setting=None
    try:
        system_setting=SystemSetting.objects.filter(user=request.user).first()
    except:
        pass
    
    try:
        notifications=Notification.objects.filter(user=request.user,closed=False,displaytime__lte=datetime.datetime.now())
        
        if (system_setting and not system_setting.notification_for_report) or ( system_setting==None):    
            notifications=notifications.exclude(pk__in= TaskTime.objects.filter(user=request.user).exclude(tasktime_notification=None).values_list('tasktime_notification__pk', flat=True))

        if (system_setting and not system_setting.notification_for_confirm_report) or ( system_setting==None):
            notifications=notifications.exclude(pk__in=Report.objects.filter(task_time__user__pk__in=request.user.employee.GetDirectChildrenUserId).exclude(confirmed_notification=None).values_list('confirmed_notification__pk',flat=True))

        if (system_setting and not system_setting.notification_for_task_times) or ( system_setting==None):
            notifications=notifications.exclude(pk__in=Task.objects.filter(user_assignee=request.user).exclude(startdate_notification=None).values_list('startdate_notification__pk', flat=True))
            notifications=notifications.exclude(pk__in=Task.objects.filter(user_assignee=request.user).exclude(enddate_notification=None).values_list('enddate_notification__pk', flat=True))

        

        data["notification_number"]=notifications.count()
    except Exception as err:
        data['message']=err.args[0]
    return JsonResponse(data)

@login_required(login_url='user:login') #redirect when user is not logged in
def GetRequestNumber(request):
    data={}
    if len(request.user.locumtenens_organization_groups.all())>0 and request.user.locumtenens_organization_groups.first().locumtenens_active:
        as_user = request.user.locumtenens_organization_groups.first().manager
        
    else:
        as_user=request.user
    
    try:
        task_verification_log = Task_Verification_Log.objects.filter(pk = -1)
        if Organization_Group.objects.get(pk=request.user.employee.organization_group.id).locumtenens_active:
            task_verification_log = Task_Verification_Log.objects.filter(Q(verified=None,verifier=request.user)|Q(verified=None,verifier_locumtenens=request.user))\
                .filter(pk__in=Task_Verification_Log.objects.values('task').exclude(task__in=Task_Verification_Log.objects.filter(verified=False).values('task'))\
                    .exclude(verified=True).values('id'))
        else:
            task_verification_log = Task_Verification_Log.objects.filter(Q(verified=None,verifier=request.user))\
                .filter(pk__in=Task_Verification_Log.objects.values('task').exclude(task__in=Task_Verification_Log.objects.filter(verified=False).values('task'))\
                    .exclude(verified=True).values('id'))
    except:
        pass

    task_requests=Task_Assign_Request.objects.filter(status=None, task__user_assignee=None,notification_status=None,user=request.user).exclude(need_verification=True).exclude(task__assign_status__lte = 2).exclude(task__cancelled = True).exclude(task__confirmed = True).exclude(task__public = True)

    if request.user.employee.in_staff_group or as_user.employee.GetEmployeeTopParent == as_user:
        feedbacks_comment = Feedback.objects.filter(feedback_type__needs_verification = True , comment = None)
    else:
        feedbacks_comment = Feedback.objects.filter(pk = -1)

    if as_user.employee.GetEmployeeTopParent == as_user:
        feedbacks_verif = Feedback.objects.filter(feedback_type__needs_verification = True , verified = False, rejected = False).exclude( comment = None)
    else:
        feedbacks_verif = Feedback.objects.filter(pk = -1)

    feedbacks_invest = Feedback.objects.filter(feedback_type__needs_investigation = True , feedback_type__investigator = request.user , investigated = False)\
        .exclude(feedback_type__needs_verification = True , verified = False)

    
    try:
        task_verification_log = task_verification_log.exclude(task__assign_status__lte = 2).exclude(task__cancelled = True).exclude(task__confirmed = True).exclude(task__public = True)
        data["request_number"]= feedbacks_invest.count() + feedbacks_verif.count() + feedbacks_comment.count() + task_verification_log.count() + task_requests.count()
    except Exception as err:
        data['message']=err.args[0]
    return JsonResponse(data)



@login_required(login_url='user:login') #redirect when user is not logged in
def GetNotificationMessages(request):
    data={}
    system_setting=None
    try:
        system_setting=SystemSetting.objects.filter(user=request.user).first()
    except:
        pass
    try:
        # task_requests=Task_Assign_RequestSerializer(Task_Assign_Request.objects.filter(status=None,notification_status=None,user=request.user), many=True)
        # data["task_requests"]=JSONRenderer().render(task_requests.data).decode("utf-8")  

        notifications=Notification.objects.filter(user=request.user,closed=False,displaytime__lte=datetime.datetime.now())

        if (system_setting and not system_setting.notification_for_report) or ( system_setting==None):    
            notifications=notifications.exclude(pk__in= TaskTime.objects.filter(user=request.user).exclude(tasktime_notification=None).values_list('tasktime_notification__pk', flat=True))

        if (system_setting and not system_setting.notification_for_confirm_report) or ( system_setting==None):
            notifications=notifications.exclude(pk__in=Report.objects.filter(task_time__user__pk__in=request.user.employee.GetDirectChildrenUserId).exclude(confirmed_notification=None).values_list('confirmed_notification__pk',flat=True))

        if (system_setting and not system_setting.notification_for_task_times) or ( system_setting==None):
            notifications=notifications.exclude(pk__in=Task.objects.filter(user_assignee=request.user).exclude(startdate_notification=None).values_list('startdate_notification__pk', flat=True))
            notifications=notifications.exclude(pk__in=Task.objects.filter(user_assignee=request.user).exclude(enddate_notification=None).values_list('enddate_notification__pk', flat=True))

        data["notifications"]=JSONRenderer().render(notifications.values('pk','title','link','messages')).decode("utf-8")
        
    except Exception as err:
        data['message']=err.args[0]
    return JsonResponse(data)

@login_required(login_url='user:login') #redirect when user is not logged in
def AcceptNotification(request,id):
    data={}
    try:
        notification=Notification.objects.get(pk=id,user=request.user)
        if notification:
            notification.closed=True
            notification.save()
            data['message']="انجام شد"
            return JsonResponse(data)
            
        
    except Exception as err:
        data['message']="لطفا دوباره سعی کنید"
    return JsonResponse(data)