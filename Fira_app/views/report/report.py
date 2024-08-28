from django.db.models import Q, IntegerField
from django.shortcuts import render, redirect
from django.http import HttpResponse, Http404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from ...models import TaskTime,Report,ReportAttachment,ReportComment,Notification,Task,\
    SystemPublicSetting, ReportExtension,Organization_Group
import datetime
from jdatetime import datetime as jdt
from ...utilities.date_tools import ConvertToMiladi, ConvertToSolarDate,DateTimeDifference,ConvertTimeDeltaToStringTime
from django.http import JsonResponse
from ...Serializers.time_report_serializer import *
from django.core import serializers
from rest_framework.renderers import JSONRenderer
from django.core.exceptions import PermissionDenied
from django.db.models import Value,BooleanField
from django.contrib.postgres.search import TrigramSimilarity
from django.contrib.postgres.search import SearchVector, SearchQuery,SearchRank
import json

# function to add attachment to a report
@login_required(login_url='user:login') #redirect when user is not logged in
def AddAttachment(request,report_id):
    data={}
    if request.method=="POST":
        try:
            _report=Report.objects.get(pk=report_id)
            if _report.task_time.user == request.user :
                attachment=ReportAttachment()
                if 'report_add_attachment_modal_file_input' in request.FILES:
                    _file=request.FILES['report_add_attachment_modal_file_input']
                    attachment.attachment_file = _file
                    attachment.filename=request.POST["report_add_attachment_modal_filename"]
                    attachment.name = request.POST["report_add_attachment_modal_title"]
                    attachment.report=_report
                   
                    attachment.save()
                    data['message']="فایل با موفقیت ذخیره شد"
                else:
                    data['message']="فایلی جهت ارسال انتخاب نشده است"
            else:
                raise PermissionDenied
        except Exception as err:
            data['message']=err.args[0]
    return JsonResponse(data)
            
# return list of report attachments 
@login_required(login_url='user:login') #redirect when user is not logged in
def AttachmentToList(request,report_id):
    if len(request.user.locumtenens_organization_groups.all())>0 and request.user.locumtenens_organization_groups.first().locumtenens_active:
        as_user = request.user.locumtenens_organization_groups.first().manager
    else:
        as_user = request.user

    tasks = Task.objects.filter(
        Q(creator=request.user) | Q(user_assignee=request.user)|Q(creator__pk__in=request.user.employee.GetAllChildrenUserId)|Q(user_assignee__pk__in=as_user.employee.GetAllChildrenUserId)\
        |Q(pk__in=request.user.employee.UnderTaskGroupTasks)|Q(pk__in=request.user.employee.CopyFromAccessTasks)|Q(group_assignee__head__pk__in=as_user.employee.GetAllChildrenUserId)) 
    
    data={}
    try:
        _report=Report.objects.get(pk=int(report_id))
        if _report.task_time.task in tasks or  (_report.task_time.task.public and (request.user == _report.task_time.user or request.user.id in _report.task_time.user.employee.GetEmployeeParentSet or request.user.id in _report.task_time.user.employee.GetEmployeeParentLocumtenensSet)):
            _files=serializers.serialize('json',ReportAttachment.objects.filter(report_id=report_id))
            data["files"]=_files
        else:
            raise PermissionDenied
        
    except Exception as err:
        data['message']=err.args[0]
            
        
    return JsonResponse(data)
    
# function for delete report attachment
@login_required(login_url='user:login') #redirect when user is not logged in
def DeleteAttachment(request,id):
    data={}
    try:
        _report_file=ReportAttachment.objects.get(pk=id)
        if _report_file.user == request.user :
            _report_file.attachment_file.delete()
            _report_file.delete()
            data["message"]="حذف با موفقیت انجام شد"
        else:
            raise PermissionDenied
    except Exception as err:
        data['message']=err.args[0]
    return JsonResponse(data)



# this function return reports list
@login_required(login_url='user:login') #redirect when user is not logged in
def ReportsList(request):   #**kwargs
    if len(request.user.locumtenens_organization_groups.all())>0 and request.user.locumtenens_organization_groups.first().locumtenens_active:
        as_user = request.user.locumtenens_organization_groups.first().manager
    else:
        as_user = request.user

    _user = request.user
    this_user = User.objects.get(pk=_user.id)
    request.session["activated_menu"]="report_list"
    context = {}
    try:
        if (not request.user.employee.organization_group.group_parent  and request.user.employee.organization_group.manager==request.user):
            context["has_parent"]=False
        else:
            context["has_parent"]=True
    except:
        pass
    tasks = Task.objects.filter(
        Q(creator=request.user) | Q(user_assignee=request.user)|Q(creator__pk__in=request.user.employee.GetAllChildrenUserId)|Q(user_assignee__pk__in=as_user.employee.GetAllChildrenUserId)\
            |Q(pk__in=request.user.employee.UnderTaskGroupTasks)|Q(pk__in=request.user.employee.CopyFromAccessTasks)|Q(group_assignee__head__pk__in=as_user.employee.GetAllChildrenUserId))\
                .only('id','name','task_parent').select_related('task_parent')

    
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
    context["report_list_task_tree"] = _tree
    
    
    context["current_user_id"] = request.user.id
    context["children_user"]=None
    context["isManager"]=False
    context["user"] = User.objects.all().exclude(username='admin').order_by('last_name')

    if(request.user.employee.organization_group.manager==request.user or as_user!=request.user):
        context["isManager"]=True 
        _children=User.objects.filter(is_active=True).filter(pk__in=as_user.employee.GetAllChildrenUserId).exclude(pk=request.user.id).order_by('last_name')
        context["children_user"] =_children 
    context["direct_children"] = as_user.employee.GetDirectChildrenUserId | request.user.employee.GetDirectChildrenUserId
    # Page default : Load all recent not confirmed reports from children
    if len(request.GET) == 0 and context["isManager"] == True:
        filtered_reports = Report.objects.filter(confirmed=False,task_time__user__id__in=context["direct_children"])\
            .exclude(task_time__teleworking=False,created__lte=(datetime.datetime.today()-datetime.timedelta(days=10)))\
                .exclude(task_time__teleworking=True,created__lte=(datetime.datetime.today()-datetime.timedelta(days=60)))\
                    .reverse()

        context["report_list_reports"] =  filtered_reports
        context["report_list_selected_user_name"]= "همه"
        context["report_list_selected_user_id"] = -1
        context["report_list_selected_task_id"] = 0
        context["report_list_selected_task_name"] = "همه کارها"
        context["report_list_selected_report_type"] = 0
        try:
            context["report_list_selected_from_date"] = ConvertToSolarDate(filtered_reports.last().task_time.end.date())
            context["report_list_selected_to_date"] = ConvertToSolarDate(filtered_reports.first().task_time.end.date())
            context["report_list_selected_report_id"] = filtered_reports.last().id
        except:
            context["report_list_selected_from_date"] = ConvertToSolarDate(datetime.datetime.today())
            context["report_list_selected_to_date"] = ConvertToSolarDate(datetime.datetime.today())
            context["report_list_selected_report_id"] =0

        return render(request, 'report/list.html', {'context':context})
        
    # u_id is selected user id in parameters    
    try:
        selected_user_id = int(request.GET.get("u_id",""))
        # id -1  is used for select all users in combobox
        if selected_user_id == -1 :
            context["report_list_selected_user_name"]= "همه"
        else:
            # if request user id is deifferent of selected user id
            if this_user.id != selected_user_id:
                if selected_user_id not in as_user.employee.GetAllChildrenUserId:
                    raise PermissionDenied
                else:
                    context["report_list_selected_user_name"] = User.objects.get(pk=selected_user_id).employee.FullName
            else:
                context["report_list_selected_user_name"] = User.objects.get(pk=selected_user_id).employee.FullName
    except:
        selected_user_id = 0
    context["report_list_selected_user_id"] = selected_user_id
    context["request_user_id"]=this_user.id
    
    # t_id is selected task id in parameters
    try:
        selected_task_id = int(request.GET.get("t_id",""))
        task = Task.objects.get(id=selected_task_id)
        selected_task_family_id = task.GetAllTaskChildrenId
        selected_task_family_id.add(selected_task_id)
        if task not in tasks:
            selected_task_id = 0
    except:
        selected_task_id = 0
    context["report_list_selected_task_id"]= selected_task_id

    # 0 is not a task id and is used for choose all tasks
    if selected_task_id != 0:
        context["report_list_selected_task_name"] =Task.objects.get(id = selected_task_id).name
    else:
        context["report_list_selected_task_name"] = "همه کارها"

    # r_type is used to select report types
    try:
        selected_report_type = int(request.GET.get("r_type",""))
    except:
        selected_report_type = 0
    context["report_list_selected_report_type"]= selected_report_type

    # pn_day is previous and next day. if this item be 1, it means user selects next day. if -1 means previous day and if 0 nothing
    try:
        selected_pn_date = int(request.GET.get("pn_day",""))
    except:
        selected_pn_date = 0

    # f_day means "from day". used for select first day of a range
    try:
        selected_from_date = request.GET.get("f_day","")
        # format of f_day is hijri and need to be converted to gregorian
        selected_from_date = jdt.strptime(selected_from_date + " 00:00",'%Y/%m/%d %H:%M').togregorian()
    except:
        if int(request.GET.get("t_id","0")) > 0:
            selected_from_date = Task.objects.get(id=selected_task_id).created
        else:
            # this row create time format of today to  YYYY/MM/DD-00:00:00
            selected_from_date = datetime.datetime.combine(datetime.date.today() , datetime.datetime.min.time())
    context["report_list_selected_from_date"] = ConvertToSolarDate(selected_from_date)
    
    # t_day means "to day". used for select last day of a range
    try:
        selected_to_date = request.GET.get("t_day","")
        # format of t_day is hijri and need to be converted to gregorian
        selected_to_date =  jdt.strptime(selected_to_date + " 23:59",'%Y/%m/%d %H:%M').togregorian()    
    except:
        # this row create time format of today to  YYYY/MM/DD-23:59:59
        selected_to_date = datetime.datetime.combine(datetime.date.today() , datetime.time(23,59,59))
    context["report_list_selected_to_date"] = ConvertToSolarDate(selected_to_date)

    # search means "Search input string" for search input
    try:
        search_string = request.GET.get("search","")
    except:
        search_string = ""
    context["report_list_search_string"] = search_string

    # previous and next day selection
    try:
        # for select next day
        if selected_pn_date == 1:
            selected_from_date =  selected_from_date + datetime.timedelta(days=1)
            selected_to_date = selected_to_date + datetime.timedelta(days=1)
            context["report_list_selected_from_date"] = ConvertToSolarDate(selected_from_date)
            context["report_list_selected_to_date"] = ConvertToSolarDate(selected_to_date)
        #for select previous day
        elif selected_pn_date == -1:
            selected_from_date =  selected_from_date + datetime.timedelta(days=-1)
            selected_to_date = selected_to_date + datetime.timedelta(days=-1)
            context["report_list_selected_from_date"] = ConvertToSolarDate(selected_from_date)
            context["report_list_selected_to_date"] = ConvertToSolarDate(selected_to_date)
    except:
        pass

    # r_id is used to identify selected report id
    try:
        selected_report_id = int(request.GET.get("r_id",""))
    except:
        # if r_id = 0 means no report selected
        selected_report_id = 0
    context["report_list_selected_report_id"]= selected_report_id

    if selected_report_id != 0:
        report = Report.objects.get(pk = selected_report_id)
        selected_user_id = report.task_time.user.id  
        selected_from_date = datetime.datetime.combine(report.task_time.start.date() , datetime.datetime.min.time())
        selected_to_date = datetime.datetime.combine(report.task_time.end.date() , datetime.time(23,59,59))
        context["report_list_selected_from_date"] = ConvertToSolarDate(selected_from_date)
        context["report_list_selected_to_date"] = ConvertToSolarDate(selected_to_date)
        context["report_list_selected_user_id"] = selected_user_id

    # this section filters reports, based on specified parameters
    children_and_self_id = as_user.employee.GetAllChildrenUserId
    if as_user != request.user:
        children_and_self_id.add(request.user.id)

    filtered_reports = Report.objects.filter(task_time__start__gte = selected_from_date,task_time__end__lte = selected_to_date, draft=0)

    if selected_task_id != 0 and( selected_task_id in request.user.employee.CopyFromAccessTasks or  selected_task_id in request.user.employee.UnderTaskGroupTasks):
        pass
    else:
        if selected_user_id == 0:
            filtered_reports = filtered_reports.filter(task_time__user__id=_user.id)
        elif selected_user_id == -1:
            filtered_reports = filtered_reports.filter(task_time__user__id__in = children_and_self_id)
        else:
            if selected_user_id in as_user.employee.GetAllChildrenUserId or selected_user_id == request.user.id or selected_user_id == as_user.id:
                filtered_reports = filtered_reports.filter(task_time__user__id=selected_user_id)
            else :
                if (report.group_shared and request.user.pk in report.task_time.user.employee.organization_group.GetGroupMembersId())\
                    or (request.user in report.shared_users.all()):
                    filtered_reports = Report.objects.filter(pk = selected_report_id)
                else:
                    raise PermissionDenied
    
    if selected_task_id != 0:
        filtered_reports = filtered_reports.filter(task_time__task__id__in=selected_task_family_id)
    else:
        pass
    if selected_report_type > 0 and selected_report_type<=3:
        filtered_reports = filtered_reports.filter( report_type = selected_report_type)
    else:
        if selected_report_type==4:
           filtered_reports = filtered_reports.filter(pk__in=ReportAttachment.objects.all().values_list('report__pk',flat=True))

    if search_string != "":
        search_vector = SearchVector('title', weight='A') + SearchVector('content', weight='B')
        search_q = SearchQuery(search_string)
        new_filtered_reports = filtered_reports.annotate(rank=SearchRank(search_vector, search_q)).filter(rank__gte=0.2).order_by('-rank')
        if new_filtered_reports.count() == 0:
            filtered_reports = filtered_reports.annotate(similarity=TrigramSimilarity('content', search_string) + (0.5*TrigramSimilarity('title', search_string)),).filter(similarity__gt=0.15).order_by('-similarity')
        else:
            filtered_reports = new_filtered_reports
    else:
        # reverse arrange of reports
        filtered_reports = filtered_reports.reverse()
        
    
    context["report_list_reports"] =  filtered_reports

    return render(request, 'report/list.html', {'context':context}) #,'report':report


# function to return report details.
@login_required(login_url='user:login') #redirect when user is not logged in
def GetReportDetail(request,report_id):
    if len(request.user.locumtenens_organization_groups.all())>0 and request.user.locumtenens_organization_groups.first().locumtenens_active:
        as_user = request.user.locumtenens_organization_groups.first().manager
    else:
        as_user = request.user

    tasks = Task.objects.filter(
        Q(creator=request.user) | Q(user_assignee=request.user)|Q(creator__pk__in=request.user.employee.GetAllChildrenUserId)|Q(user_assignee__pk__in=as_user.employee.GetAllChildrenUserId)\
        |Q(pk__in=request.user.employee.UnderTaskGroupTasks)|Q(pk__in=request.user.employee.CopyFromAccessTasks)|Q(group_assignee__head__pk__in=as_user.employee.GetAllChildrenUserId)) 
        
    data={}
    try:
        _report=Report.objects.get(pk=int(report_id))
        _task = _report.task_time.task
        _parents = Task.objects.filter(pk__in = _task.GetTaskParentIDSet)
        _parents_title = ''
        while True and _parents.count() > 0 and _task.task_parent:
            if _parents.filter(pk = _task.task_parent.id).exists():
                _task = _task.task_parent
                _parents_title = ">" +_task.name  + _parents_title
            else:
                break
        if _report.task_time.task in tasks or  \
            (_report.task_time.task.public and (request.user == _report.task_time.user or request.user.id in _report.task_time.user.employee.GetEmployeeParentSet or request.user.id in _report.task_time.user.employee.GetEmployeeParentLocumtenensSet)) or\
                (_report.group_shared and request.user.pk in _report.task_time.user.employee.organization_group.GetGroupMembersId())\
                    or (request.user in _report.shared_users.all()):
            reports=ReportSerializer(Report.objects.filter(pk=report_id), many=True)
            data["report"]=JSONRenderer().render(reports.data).decode("utf-8") 
            _tags=''
            for t in _report.tags.all():
                _tags+=t.name+','
            data["report_tag"]=_tags
            Extensions = ReportExtensionSerializer(ReportExtension.objects.filter(report = _report) , many = True)
            data["report_extension"] =JSONRenderer().render(Extensions.data).decode("utf-8")
            if request.user != _report.task_time.user:
                data["report_parents_title"] = _parents_title
            else:
                if _report.task_time.task.task_parent:
                    data["report_parents_title"] = _report.task_time.task.name + '>' + _report.task_time.task.task_parent.name
                else :
                    data["report_parents_title"] = _report.task_time.task.name 
        else:
            raise PermissionDenied
    except Exception as err:
        data['message']=err.args[0]
    return JsonResponse(data)

# function for add comment to a report
@login_required(login_url='user:login') #redirect when user is not logged in
def AddComment(request):
    data={}
    if request.method=="POST":
        try:
            # create comment report object
            comment=ReportComment()
            comment.content=request.POST["report_list_comment_new_message_input"]
            report=Report.objects.get(pk=int(request.POST["task_list_selected_report_id"]))
            if report.task_time.user ==request.user or request.user.id in report.task_time.user.employee.GetEmployeeParentSet or request.user.id in report.task_time.user.employee.GetEmployeeParentLocumtenensSet:
                comment.report=report
                comment.user=request.user
                comment.save()

                # notification send to report owner 
                if report.task_time.user !=request.user:
                    try:
                        notification=Notification.objects.get(pk=report.comment_notification.pk)
                    except:
                        notification=Notification()
                    notification.title="نظر خوانده نشده "
                    notification.user=report.task_time.user
                    notification.displaytime=datetime.datetime.now()
                    notification.messages=request.user.first_name+" "+request.user.last_name +" در تاریخ "+ConvertToSolarDate(datetime.datetime.now()) + "  برای گزارش روز "+ConvertToSolarDate(report.task_time.start )+" مربوط به کار  "+ report.task_time.task.name +" نظری ثبت کرده است "
                    notification.link="/report/list/?r_id=" +str(report.id)  
                    notification.closed=False
                    notification.save()

                    report.comment_notification=notification
                    report.save()

                data["message"]="نظر شما با موفقیت ثبت شد"
            else:
                raise PermissionDenied
        except Exception as err:
            data['message']=err.args[0]
            
    return JsonResponse(data)

# function for send all comments of a report  to user
@login_required(login_url='user:login') #redirect when user is not logged in
def GetCommentList(request,report_id):
    if len(request.user.locumtenens_organization_groups.all())>0 and request.user.locumtenens_organization_groups.first().locumtenens_active:
        as_user = request.user.locumtenens_organization_groups.first().manager
    else:
        as_user = request.user

    tasks = Task.objects.filter(
        Q(creator=request.user) | Q(user_assignee=request.user)|Q(creator__pk__in=request.user.employee.GetAllChildrenUserId)|Q(user_assignee__pk__in=as_user.employee.GetAllChildrenUserId)\
        |Q(pk__in=request.user.employee.UnderTaskGroupTasks)|Q(pk__in=request.user.employee.CopyFromAccessTasks)|Q(group_assignee__head__pk__in=as_user.employee.GetAllChildrenUserId)) 
    
    data={}
    try:
        # serialize all comments of a report
        _report=Report.objects.get(pk=int(report_id))
        if _report.task_time.task in tasks or  (_report.task_time.task.public and (request.user == _report.task_time.user or request.user.id in _report.task_time.user.employee.GetEmployeeParentSet or request.user.id in _report.task_time.user.employee.GetEmployeeParentLocumtenensSet)):
            comments=ReportCommentSerializer(ReportComment.objects.filter(report__id=report_id), many=True)
            data["comments"]=JSONRenderer().render(comments.data).decode("utf-8") 
        else:
            raise PermissionDenied
    except Exception as err:
        data['message']=err.args[0]
            
    return JsonResponse(data)

# function for delete a report
@login_required(login_url='user:login') #redirect when user is not logged in
def DeleteReport(request,report_id):
    try:
        _report=Report.objects.get(pk=int(report_id))
        if _report.task_time.user == request.user :
            
            # delete time notification
            if (_report.confirmed_notification):
                notification=Notification.objects.get(pk=_report.confirmed_notification.pk)
                notification.delete()
            
            if (_report.comment_notification):
                notification=Notification.objects.get(pk=_report.comment_notification.pk)
                notification.delete()
            
            _report.delete()
            _report.task_time.TimeLineColorUpdate()
            return  HttpResponse(True)
        else:
            raise PermissionDenied
    except Exception as err:
        return  HttpResponse(False)
            
    return  HttpResponse(False)

# function for confirm reports
@login_required(login_url='user:login') #redirect when user is not logged in
def ConfirmReport(request,report_id,score):
    try:
        _report=Report.objects.get(pk=int(report_id))
        
        # user authentication condition
        if  _report.task_time.user.id in request.user.employee.GetDirectChildrenUserId or _report.task_time.user.id in request.user.employee.GetDirectChildrenForLocumtenenseUserId or (not request.user.employee.organization_group.group_parent and request.user.employee.organization_group.manager==request.user) :
            # time expire conditions
            if SystemPublicSetting.objects.first() and SystemPublicSetting.objects.first().accepting_reports_limit_days > 0 :
                if (datetime.datetime.now() - _report.created.replace(tzinfo=None)).total_seconds() > (SystemPublicSetting.objects.first().accepting_reports_limit_days * 24 + 5) * 3600:
                    return HttpResponse(False)


            if _report.task_time.user.id in request.user.employee.GetDirectChildrenForLocumtenenseUserId:
                _report.confirmed_by_locumtenens=True
            
            _report.confirmed=True
            _report.score=score
            _report.save()
            ############################## notification
            #delete time notification
            if (_report.confirmed_notification):
                notification=Notification.objects.get(pk=_report.confirmed_notification.pk)
                notification.closed=True
                notification.save()
            _report.task_time.TimeLineColorUpdate()
            return  HttpResponse(True)
        else:
            
            raise PermissionDenied
    except Exception as err:
        return  HttpResponse(False)
            
    return  HttpResponse(False)


# Share report with others
@login_required(login_url='user:login') #redirect when user is not logged in
def ReportShare(request,report_id):
    if request.method=="POST":
        try:
            _report=Report.objects.get(pk=int(report_id))
            
            # user authentication condition
            if  _report.task_time.user.id in request.user.employee.GetDirectChildrenUserId or _report.task_time.user.id in request.user.employee.GetDirectChildrenForLocumtenenseUserId or (not request.user.employee.organization_group.group_parent and request.user.employee.organization_group.manager==request.user) :
                share_users = User.objects.filter(pk__in = json.loads(request.POST['id_l']))
                for deleted_user in _report.shared_users.exclude(pk__in = json.loads(request.POST['id_l'])):
                    _report.shared_users.remove(deleted_user)
                share_users = share_users.exclude(pk__in = _report.shared_users.values_list('pk',flat=True))
                ############################## notification
                for s_user in share_users:
                    _report.shared_users.add(s_user)
                    notification=Notification()
                    notification.title="اشتراک گذاری گزارش"
                    notification.user=s_user
                    # notification will display to manager after 2 days
                    notification.displaytime=datetime.datetime.now()
                    notification.messages="گزارش "+ _report.task_time.user.first_name+" "+ _report.task_time.user.last_name +" در تاریخ "+ConvertToSolarDate(_report.task_time.start) + " با شما به اشتراک گذاشته شد. "
                    notification.link="/report/list/?r_id=" +str(_report.id)  
                    notification.save()
                
                _report.save()
                return  HttpResponse("اشتراک گذاری انجام شد")
            else:
                
                raise PermissionDenied
        except Exception as err:
            return  HttpResponse("اشتراک گذاری ناموفق بود")
    else:
        try:
            _report=Report.objects.get(pk=int(report_id))
            
            # user authentication condition
            if  _report.task_time.user.id in request.user.employee.GetDirectChildrenUserId or _report.task_time.user.id in request.user.employee.GetDirectChildrenForLocumtenenseUserId or (not request.user.employee.organization_group.group_parent and request.user.employee.organization_group.manager==request.user) :

                return  JsonResponse(list(_report.shared_users.all().values_list('pk', flat=True)),safe=False)
            else:
                
                raise PermissionDenied
        except Exception as err:
            return  JsonResponse([])
            
    


# Share report with teammates
@login_required(login_url='user:login') #redirect when user is not logged in
def ReportShareGroup(request,report_id):
    try:
        _report=Report.objects.get(pk=int(report_id))
        
        # user authentication condition
        if  _report.task_time.user.id in request.user.employee.GetDirectChildrenUserId or _report.task_time.user.id in request.user.employee.GetDirectChildrenForLocumtenenseUserId or (not request.user.employee.organization_group.group_parent and request.user.employee.organization_group.manager==request.user) :

            _report.group_shared=not(_report.group_shared)
            _report.save()
            ############################## notification
            #send notification to teammates
            if _report.group_shared:
                for teammate in User.objects.filter(employee__organization_group = _report.task_time.user.employee.organization_group).exclude(id = request.user.id):
                    notification=Notification()
                    notification.title="اشتراک گذاری گزارش"
                    notification.user=teammate
                    # notification will display to manager after 2 days
                    notification.displaytime=datetime.datetime.now()
                    notification.messages="گزارش "+ _report.task_time.user.first_name+" "+ _report.task_time.user.last_name +" در تاریخ "+ConvertToSolarDate(_report.task_time.start) + " با شما به اشتراک گذاشته شد. "
                    notification.link="/report/list/?r_id=" +str(_report.id)  
                    notification.save()
            return  HttpResponse(True)
        else:
            
            raise PermissionDenied
    except Exception as err:
        return  HttpResponse(False)
            
    return  HttpResponse(False)


# Add report to month report
@login_required(login_url='user:login') #redirect when user is not logged in
def MonthReport(request,report_id):
    try:
        _report=Report.objects.get(pk=int(report_id))
        
        # user authentication condition
        if  _report.task_time.user.id in request.user.employee.GetDirectChildrenUserId or _report.task_time.user.id in request.user.employee.GetDirectChildrenForLocumtenenseUserId or (not request.user.employee.organization_group.group_parent and request.user.employee.organization_group.manager==request.user) :

            _report.month_report=not(_report.month_report)
            _report.save()

            return  HttpResponse(True)
        else:
            
            raise PermissionDenied
    except Exception as err:
        return  HttpResponse(False)
            
    return  HttpResponse(False)

# Get month report page content
@login_required(login_url='user:login') #redirect when user is not logged in
def MonthReportList(request):
    request.session["activated_menu"]="month_report"
    context = {}
    if not request.user.employee.IsManager:
        raise PermissionDenied


    subgroups = Organization_Group.objects.filter(group_parent = request.user.employee.organization_group)
    
    subgroups |= Organization_Group.objects.filter(id = request.user.employee.organization_group.id)

    context["subgroups"] = subgroups
    try:
        selected_subgroup_id = int(request.GET.get("g_id",""))
        selected_subgroup = subgroups.get(id = selected_subgroup_id)
    except:
        selected_subgroup = request.user.employee.organization_group

    context["selected_subgroup"] = selected_subgroup

    tasks = Task.objects.filter(
        Q(creator=selected_subgroup.manager) | Q(user_assignee=selected_subgroup.manager)|Q(creator__pk__in=selected_subgroup.manager.employee.GetAllChildrenUserId)|Q(user_assignee__pk__in=selected_subgroup.manager.employee.GetAllChildrenUserId)\
            |Q(pk__in=selected_subgroup.manager.employee.UnderTaskGroupTasks)|Q(pk__in=selected_subgroup.manager.employee.CopyFromAccessTasks)|Q(group_assignee__head__pk__in=selected_subgroup.manager.employee.GetAllChildrenUserId))\
                .only('id','name','task_parent').select_related('task_parent')

    
    parent_tasks = tasks.exclude(task_parent__pk__in=tasks.values_list('pk',flat=True))

    context["parent_tasks"] = parent_tasks

    all_tasks = Task.objects.filter(pk = -1)
    try:
        parent_tasks_temp = parent_tasks
        all_tasks  |= parent_tasks_temp
        for layers in range(10):
            parent_tasks_temp = Task.objects.filter(task_parent__pk__in=parent_tasks_temp.values_list('pk',flat=True))
            if len(parent_tasks) == 0:
                break
            else:
                all_tasks |= parent_tasks_temp
    except:
        pass


    # f_day means "from day". used for select first day of a range
    try:
        selected_from_date = request.GET.get("f_day","")
        # format of f_day is hijri and need to be converted to gregorian
        selected_from_date = jdt.strptime(selected_from_date + " 00:00",'%Y/%m/%d %H:%M').togregorian()
    except:
        selected_from_date = datetime.datetime.combine(datetime.date.today() - datetime.timedelta(days=30) , datetime.datetime.min.time())
    context["report_list_selected_from_date"] = ConvertToSolarDate(selected_from_date)
    
    # t_day means "to day". used for select last day of a range
    try:
        selected_to_date = request.GET.get("t_day","")
        # format of t_day is hijri and need to be converted to gregorian
        selected_to_date =  jdt.strptime(selected_to_date + " 23:59",'%Y/%m/%d %H:%M').togregorian()    
    except:
        # this row create time format of today to  YYYY/MM/DD-23:59:59
        selected_to_date = datetime.datetime.combine(datetime.date.today() , datetime.time(23,59,59))
    context["report_list_selected_to_date"] = ConvertToSolarDate(selected_to_date)

    reports = Report.objects.filter(task_time__start__gte = selected_from_date, task_time__end__lte = selected_to_date, month_report = True, task_time__task__in = all_tasks)

    selected_tasks = all_tasks.filter(id__in = reports.values_list("task_time__task__id", flat = True)).order_by("id")
    
    selected_tasks.annotate(parent_task_id = Value(0,IntegerField()))

    selected_task_parents = Task.objects.filter(pk = -1)
    for task in selected_tasks:
        try:
            task.parent_task_id = parent_tasks.filter(id__in = task.GetTaskParentIDSet)[0].id
            selected_task_parents |= parent_tasks.filter(id__in = task.GetTaskParentIDSet)
        except:
            pass

    context['reports'] = reports
    context['selected_tasks'] = selected_tasks
    context['selected_task_parents'] = selected_task_parents

    return render(request, 'report/month.html', {'context':context})