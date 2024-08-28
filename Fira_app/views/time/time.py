from django.shortcuts import render, redirect
from django.http import HttpResponse, Http404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from ...models import Task,PublicTask,TaskTime,PublicTaskTime,TempTimingRecord,Report,Notification,ReportAttachment,SystemPublicSetting, ReportExtension
from ...forms import ReportContentForm
import datetime 
from jdatetime import datetime as jdt
from ...Serializers.time_report_serializer import *
from ...utilities.date_tools import ConvertToMiladi, ConvertToSolarDate,GetWeekDay,DateTimeDifference,ConvertTimeDeltaToStringTime
from django.http import JsonResponse
from django.db.models import Q,Value,CharField, SmallIntegerField, BooleanField
from django.core import serializers
from rest_framework.renderers import JSONRenderer
from django.core.exceptions import PermissionDenied
from django.db import transaction
import requests


# get task children to make task tree
def GetChildren(id,user):
    task = Task.objects.get(pk=id)
    tasks = Task.objects.filter(task_parent_id=id , cancelled= False , progress__gt=0,progress__lt=100)
    s = "<li  class='nodes_time' type='private' task_name='"+task.name.replace("<","&lt;").replace(">","&gt;")+"' task_id='" + str(task.pk)+"'"+\
        (" task_type_soc" if task.task_type and task.task_type.name == "هدف مهندسی اجتماعی" else "")+ \
            ">"+("<span class='caret_time'>"+task.name.replace("<","&lt;").replace(">","&gt;")+"</span>" if not task.public else task.name.replace("<","&lt;").replace(">","&gt;"))
    if len(tasks) > 0:
        s += "<ul class='nested_time'>"
        for ch in tasks:
            if ch.user_assignee and ch.user_assignee==user:
                _children = Task.objects.filter(task_parent_id=ch.id)
                if len(_children) == 0:
                    s += "<li class='nodes_time' task_id="+str(ch.pk)+" type='private'  task_name='"+ch.name.replace("<","&lt;").replace(">","&gt;")+"'"+("task_type_soc" if ch.task_type and ch.task_type.name == "هدف مهندسی اجتماعی" else "")+">"+ch.name.replace("<","&lt;").replace(">","&gt;")+"</li>"
                else:
                    s += GetChildren(ch.pk,user)
        s += "</ul>"
    s += "</li>"
    return (s)

# main function to register time and report
@login_required(login_url='user:login') #redirect when user is not logged in
def TimeAndReport(request ,**kwargs):
    # time_id and report_id are in query string
    time_id=kwargs.get('time_id',None)
    report_id=kwargs.get('report_id',None)

    _user=request.user
    request.session["activated_menu"]="add_times"
    context={}
    context["ext_direction"] = False
    context["ext_success"] = True
    context["ext_score"] = 1
    context["ext_malicious"] = False
    context["ext_summary"] = ""
    context["ext_link_addr"] = ""
    context["ext_link_agent"] = ""
    context["ext_malware"] = ""
    context["ext_file_type"] = ""
    context["soc_task"]= False

    
    # time exists and has report 
    if (time_id and report_id):
        task_time=TaskTime.objects.get(pk=time_id)

        if task_time.task.task_type and task_time.task.task_type.name == "هدف مهندسی اجتماعی" :
            context["soc_task"]= True

        if request.user != task_time.user:
            raise PermissionDenied
        data={}
        data["time_key"]=time_id
        data["time_add_task_name"]=task_time.task.name
        data["time_add_task_key"]=task_time.task.id
        
        data["time_add_task_kind"]="private"
        data["time_start_date"]=ConvertToSolarDate(task_time.start)
        data["time_end_date"]=ConvertToSolarDate(task_time.end)
        data["time_start"]=str(task_time.start)[11:16]
        data["time_end"]=str(task_time.end)[11:16]
        data['content']=ReportContentForm()
        data["time_add_task_soc"]=('true' if task_time.task.task_type and task_time.task.task_type.name == 'هدف مهندسی اجتماعی' else 'false')
        
        report=Report.objects.get(pk=int(report_id))

        _ReportContentForm=ReportContentForm()
        _ReportContentForm.content=report.content
        context["report_content"]=report.content
        context["time_add_report_title_input"]=report.title
        context["content"]=_ReportContentForm
        context["time_add_report_type_input"] = report.report_type
        context["data"]=data
        context["mission_checkbox"]=task_time.mission
        context["teleworking_checkbox"]=task_time.teleworking
        context["time_add_start_date"]=data["time_start_date"]+"    |    "+data["time_start"]
        context["time_add_end_date"]=data["time_end_date"]+"    |    "+data["time_end"]
        context["mode"]='TimeAndReportEdit'
        context["report_id"]=report_id
        context["report_tags"]=""
        for t in report.tags.all():
            context["report_tags"]+=t.name+","
        context["time_id"]=time_id

        # if report type is not common report or result or event
        if report.report_type and report.report_type > 3:
            if report.extension :
                context["ext_direction"] = report.extension.target_started
                context["ext_success"] = report.extension.succeed
                context["ext_score"] = report.extension.enhancement_score
                context["ext_malicious"] = report.extension.malicious_file_link
                context["ext_summary"] = report.extension.chat_summary
                context["ext_link_addr"] = report.extension.link_address
                context["ext_link_agent"] = report.extension.link_user_agent
                context["ext_malware"] = report.extension.malware_type
                context["ext_file_type"] = report.extension.file_type

    # time has been registered and has not any report
    elif (time_id and not report_id):
        try:
            task_time=TaskTime.objects.get(pk=time_id)

            if task_time.task.task_type and task_time.task.task_type.name == "هدف مهندسی اجتماعی" :
                context["soc_task"]= True

            if request.user != task_time.user:
                raise PermissionDenied
            data={}
            data["time_key"]=time_id
            data["time_add_task_name"]=task_time.task.name
            data["time_add_task_key"]=task_time.task.id
            
            data["time_add_task_kind"]="private"
            data["time_start_date"]=ConvertToSolarDate(task_time.start)
            data["time_end_date"]=ConvertToSolarDate(task_time.end)
            data["time_start"]=str(task_time.start)[11:16]
            data["time_end"]=str(task_time.end)[11:16]
            data['content']=ReportContentForm()
            data["time_add_task_soc"]=('true' if task_time.task.task_type and task_time.task.task_type.name == 'هدف مهندسی اجتماعی' else 'false')
            
            _ReportContentForm=ReportContentForm()
            context["content"]=_ReportContentForm
            context["data"]=data
            context["mission_checkbox"]=task_time.mission
            context["teleworking_checkbox"]=task_time.teleworking
            context["time_add_start_date"]=data["time_start_date"]+"    |    "+data["time_start"]
            context["time_add_end_date"]=data["time_end_date"]+"    |    "+data["time_end"]
            context["mode"]='NewReport'
            context["report_id"]=0
            context["time_id"]=time_id
        except:
            return redirect("report:report_list")
    
    # if time is not registered and report does not exists
    elif (not time_id and not report_id):
        try:
            # making task tree 
            tasks = Task.objects.filter(user_assignee=request.user,cancelled=False,confirmed=False, progress__gt=0,progress__lt=100)
            tasks |= Task.objects.filter(group_assignee__head=request.user,cancelled=False, confirmed=False, progress__gt=0,progress__lt=100)
            tasks |= Task.objects.filter(public=True, cancelled = False)
            public_tasks=PublicTask.objects.all().order_by('popular')
            _tree = ""
            _tree += "<ul class='time_task_tree'>"
            for t in tasks:
                if t.task_parent is None or (t.task_parent not in tasks and t.task_parent is not None):
                    _tree += GetChildren(t.pk,request.user)

            _tree += " </ul>"
            context["tree"] = _tree
            context["mode"]='NewAll'
            _date_time_now=datetime.datetime.now()
            context["time_add_start_date"]=ConvertToSolarDate(_date_time_now)
            context["time_add_end_date"]=ConvertToSolarDate(_date_time_now + datetime.timedelta(seconds=3600))
            context["time_add_time_timedate_task_input"]=""
        except:
            pass

        context['content']=ReportContentForm()

    #  report add is in POST mood    
    if request.method == "POST":
        context["data"]=request.POST

        # report content is discovered from received text
        if "content" in request.POST and (request.POST["content"]).replace("&nbsp;","").replace(" ","").replace("\n","").replace("<p></p>","").strip() !="":
            context["report_content"]=request.POST["content"]
        
        # if task is a social task target
        if "time_add_soc_task" in request.POST and request.POST["time_add_soc_task"] == "True":
            context["soc_task"]= True

        if "time_add_report_type_input" in request.POST:
            context["time_add_report_type_input"] = int( request.POST["time_add_report_type_input"])
        

        context["ext_direction"] = bool(int(request.POST["report_body_extension_direction_input"]))
        context["ext_success"] = bool(int(request.POST["report_body_extension_success_input"]))
        context["ext_score"] = int(request.POST["report_body_extension_score_input"])
        context["ext_malicious"] = bool(int(request.POST["report_body_extension_malicious_input"]))
        context["ext_summary"] = request.POST["report_body_extension_link_summary"]
        context["ext_link_addr"] = request.POST["report_body_extension_link_addr_input"]
        context["ext_link_agent"] = request.POST["report_body_extension_link_agent_input"]
        context["ext_malware"] = request.POST["report_body_extension_malware_input"]
        context["ext_file_type"] = request.POST["report_body_extension_file_type_input"]

        # if report has tags
        if "report_tag" in request.POST:
            context["report_tags"]=request.POST["report_tag"]
        
        # report and time exist
        if time_id and report_id:
            context["mode"]='TimeAndReportEdit'
            report=Report.objects.get(pk=report_id)
            # if report has been confirmed user can not edit this
            if report.confirmed:
                context["Error"]="گزارش تائید شده و اجازه ویرایش وجود ندارد"
                context['report_content'] = request.POST["content"]  
                context["Status"]="Error"
                return render(request, 'time/add.html', {'context':context})
        # report and time not exist
        if (not time_id and not report_id): 
            # if task has not been choosed       
            if "time_add_task_key" not in request.POST:
                context["Error"] = "فیلد عنوان کار باید مقدار دهی شود"
                context['report_content'] = request.POST["content"]  
                context["Status"]="Error"
                return render(request, 'time/add.html', {'context':context})
            # if task has been choosed
            else:
                context["time_add_task_key"]=request.POST["time_add_task_key"]
                context["time_add_task_name"]=request.POST["time_add_task_name"]
                context["time_add_task_kind"]=request.POST["time_add_task_kind"]
                context["time_add_task_soc"]=request.POST["time_add_task_soc"]

            # if start time has not been choosed
            if "time_add_start_date" not in request.POST:
                context["Error"] = "فیلد تاریخ شروع باید مقدار دهی شود"
                context['report_content'] = request.POST["content"]
                context["Status"]="Error"
                return render(request, 'time/add.html', {'context':context})
            else:
                context["time_add_start_date"]=request.POST["time_add_start_date"]

            # if end time has not been choosed
            if "time_add_end_date" not in request.POST:
                context["Error"] = "فیلد تاریخ پایان باید مقدار دهی شود"
                context['report_content'] = request.POST["content"]
                context["Status"]="Error"
                return render(request, 'time/add.html', {'context':context})
            else:
                context["time_add_end_date"]=request.POST["time_add_end_date"]

            # this section is for teleworking times and reports .
            teleworking = False
            if 'time_add_teleworking_checkbox' in request.POST:
                context['teleworking_checkbox']= True
                teleworking = True
            else:
                context['teleworking_checkbox']= False
            
            # this section is for mission time and report .
            mission = False
            if 'time_add_mission_checkbox' in request.POST:
                context['mission_checkbox']= True
                mission = True
            else:
                context['mission_checkbox']= False

            # a task time can not be teleworking and misstion in a same time 
            if 'time_add_teleworking_checkbox' in request.POST and 'time_add_mission_checkbox' in request.POST:
                context["Error"] = "زمان وارد شده نمی تواند همزمان دورکاری و ماموریت باشد"
                context['report_content'] = request.POST["content"]
                context["Status"]="Error"
                return render(request, 'time/add.html', {'context':context}) 

            start_date_time=jdt.strptime(request.POST["time_add_start_date"].replace("    |    " ," "),'%Y/%m/%d %H:%M').togregorian()
            end_date_time=jdt.strptime(request.POST["time_add_end_date"].replace("    |    " ," "),'%Y/%m/%d %H:%M').togregorian()
            # if report time is over than a day this error occur
            if(start_date_time.date() != end_date_time.date()):
                context["Error"] = "امکان ثبت ساعت فراتر از یک روز وجود ندارد"
                context['report_content'] = request.POST["content"]
                context["Status"]="Error"
                return render(request, 'time/add.html', {'context':context})
            
            # if start time is biger than end time this error occur
            if (start_date_time>=end_date_time):
                context["Error"] = "زمان پایان باید بزرگتر از زمان شروع باشد"
                context['report_content'] = request.POST["content"]
                context["Status"]="Error"
                return render(request, 'time/add.html', {'context':context})
            
            _user = request.user
            # this query is used for return conflicted times if exist.
            task_time=TaskTime.objects.filter(Q(start__lte = start_date_time,end__gte = end_date_time,user =_user )\
                |Q(start__lte = start_date_time,end__gt = start_date_time,user =_user )\
                    |Q(start__lt = end_date_time,end__gte = end_date_time,user =_user )\
                        |Q(start__gte = start_date_time,end__lte = end_date_time,user =_user)\
                            |Q(start__lte = start_date_time,end__gte = end_date_time,user =_user )\
                                |Q(start__lte = start_date_time,end__gt = start_date_time,user =_user )\
                                    |Q(start__lt = end_date_time,end__gte = end_date_time,user =_user )\
                                        |Q(start__gte = start_date_time,end__lte = end_date_time,user =_user)\
                                            )
            # if conflicted time exists this error occur
            if(task_time):
                context["Error"] = "زمان وارد شده با زمان های  قبل تداخل دارد"
                context['report_content'] = request.POST["content"]
                context["Status"]="Error"
                return render(request, 'time/add.html', {'context':context})  

            # if length of time is less than 10 minute this error occur
            if (end_date_time - start_date_time).total_seconds() < 600:
                context["Error"] = "زمان وارد شده حداقل باید 10 دقیقه باشد"
                context['report_content'] = request.POST["content"]
                context["Status"]="Error"
                return render(request, 'time/add.html', {'context':context})     

            # if report time is bigger than now this error occur
            if (datetime.datetime.now() - end_date_time).total_seconds() < 0:
                context["Error"] = "امکان ثبت گزارش برای آینده وجود ندارد"
                context['report_content'] = request.POST["content"]
                context["Status"]="Error"
                return render(request, 'time/add.html', {'context':context})  

            # public system setting for report days limit
            if SystemPublicSetting.objects.first() and SystemPublicSetting.objects.first().writing_reports_limit_days > 0 and not teleworking:
                if (datetime.datetime.now() - end_date_time).total_seconds() > (SystemPublicSetting.objects.first().writing_reports_limit_days * 24 + 5) * 3600:
                    context["Error"] = "فرصت ثبت کارکرد برای زمان مد نظر شما تمام شده است"
                    context['report_content'] = request.POST["content"]
                    context["Status"]="Error"
                    return render(request, 'time/add.html', {'context':context})
            
            # system setting for teleworking registing time limit
            if SystemPublicSetting.objects.first() and SystemPublicSetting.objects.first().writing_telework_reports_limit_days > 0 and teleworking:
                try:
                    url = "http://vorud.medad-art.ir//from-date-information"
                    p_id = request.user.employee.personelnumber
                    _date = end_date_time + datetime.timedelta(days=1)
                    _date_str = str(_date.strftime(format="%Y/%m/%d"))
                    payload = {'token': 'NDI5M2VjMDgxNGRmYjlhMDMwNGJmODI5NmIwZTMzYzEwMzM2YzE3NTp7Il9hdXRoX3VzZXJfaWQiOiIzIiwiX2F1dGhfdXNlcl9iYWNrZW5kIjoiZ', 'i_date': _date_str, 'p_id': p_id}
                    files = []
                    headers= {}

                    response = requests.request("POST", url, headers=headers, data = payload, files = files)
                    response_time = datetime.datetime.strptime(response.text[:19], '%Y-%m-%d %H:%M:%S')
                    if (datetime.datetime.now() - response_time).total_seconds() > (SystemPublicSetting.objects.first().writing_telework_reports_limit_days * 24 + 5) * 3600:
                        context["Error"] = "فرصت ثبت کارکرد برای زمان مد نظر شما تمام شده است"
                        context['report_content'] = request.POST["content"]
                        context["Status"]="Error"
                        return render(request, 'time/add.html', {'context':context})
                except:
                    pass
        
        # main part for regiser time and report
        try:
            if request.POST["time_add_task_kind"]=="private":
                with transaction.atomic():
                    if (request.POST["time_add_report_add_type"]=="time" and not time_id and not report_id):   
                        # create a task time object
                        task_time=TaskTime()
                        #---------------------------------------
                        task_time.user=request.user
                        #---------------------------------------
                        _task_key = int(request.POST["time_add_task_key"])
                        task=Task.objects.get(pk=_task_key)
                        if not task.public and task.user_assignee != request.user:
                            context["Error"] = "ثبت کارکرد برای کارهایی که مسئول آن نیستید امکان پذیر نیست."
                            context['report_content'] = request.POST["content"]
                            context["Status"]="Error"
                            return render(request, 'time/add.html', {'context':context})
                        if task.cancelled:
                            context["Error"] = "ثبت کارکرد برای کارهای کنسل شده امکان پذیر نیست."
                            context['report_content'] = request.POST["content"]
                            context["Status"]="Error"
                            return render(request, 'time/add.html', {'context':context})
                        if task.task_type and task.task_type.name == "هدف مهندسی اجتماعی" :
                            context["soc_task"]= True
                        task_time.task=task


                        # task time fitures
                        task_time.start=start_date_time
                        task_time.end=end_date_time
                        task_time.mission = mission
                        task_time.teleworking = teleworking
                        #---------------------------------------
                        # task time saved here
                        task_time.save()
                        if task_time.task.task_type and task_time.task.task_type.name == "هدف مهندسی اجتماعی" :
                            context["soc_task"]= True
                            
                        ############################## notification
                        notification=Notification()
                        notification.title="ثبت گزارش"
                        notification.user=task_time.user
                        notification.displaytime=task_time.end + datetime.timedelta(days=1)
                        notification.messages=" برای کار "+task_time.task.name+" ساعت بدون گزارش ثبت شده است "
                        notification.link="/report/None/time/"+str(task_time.pk)+"/private/add/"
                        notification.save()
                        task_time.tasktime_notification=notification

                        task_time.save()

                        ############################## notification
                        context["Status"]="Saved"
                        
                        context["time_id"]=task_time.pk
                        return render(request, 'time/add.html', {'context':context})

                    ################## draft save ######################    
                    elif not request.POST["time_add_report_add_type"]=="time":
                        try:
                            
                            # report object is return or created
                            report=None
                            if (time_id and report_id):
                                report=Report.objects.get(pk=report_id)
                            else:
                                report=Report()
                            # report title
                            if "time_add_report_title_input" in request.POST:
                                report.title=request.POST["time_add_report_title_input"]
                                context["time_add_report_title_input"]=request.POST["time_add_report_title_input"]
                            # report type
                            if "time_add_report_type_input" in request.POST:
                                report.report_type=int(request.POST["time_add_report_type_input"])
                            # if report has content
                            if "content" in request.POST and (request.POST["content"]).replace("&nbsp;","").replace(" ","").replace("\n","").replace("<p></p>","").strip() !="":
                                report.content=request.POST["content"]
                            else:
                                # if report has not content
                                context["Error"]="متن گزارش را تکمیل نمائید"
                                context["Status"]="Error"
                                return render(request, 'time/add.html', {'context':context})
                            
                            # the first time for register task time
                            if (not time_id and not report_id):
                                context["time_add_report_type_input"] = 0
                                # create task time object
                                task_time=TaskTime()
                                #---------------------------------------
                                task_time.user=request.user
                                #---------------------------------------
                                _task_key = int(request.POST["time_add_task_key"])
                                task=Task.objects.get(pk=_task_key)
                                if task.task_type and task.task_type.name == "هدف مهندسی اجتماعی" :
                                    context["soc_task"]= True
                                task_time.task=task
                                #---------------------------------------
                                task_time.start=start_date_time
                                task_time.end=end_date_time
                                task_time.mission = mission
                                task_time.teleworking = teleworking
                                #---------------------------------------
                                task_time.save()
                            else:
                                task_time=TaskTime.objects.get(pk=time_id)
                                task_time.save()
                            report.task_time=task_time
                            
                            if task_time.task.task_type and task_time.task.task_type.name == "هدف مهندسی اجتماعی" :
                                context["soc_task"]= True

                            # system public setting for time over conditions
                            if SystemPublicSetting.objects.first() and SystemPublicSetting.objects.first().writing_reports_limit_days > 0 and not report.task_time.teleworking:
                                if (datetime.datetime.now() - report.task_time.end.replace(tzinfo=None)).total_seconds() > (SystemPublicSetting.objects.first().writing_reports_limit_days * 24 + 5) * 3600:
                                    context["Error"] = "فرصت ثبت گزارش برای زمان مد نظر شما تمام شده است"
                                    context['report_content'] = request.POST["content"]
                                    context["Status"]="Error"
                                    return render(request, 'time/add.html', {'context':context})

                            if SystemPublicSetting.objects.first() and SystemPublicSetting.objects.first().writing_telework_reports_limit_days > 0 and report.task_time.teleworking:
                                try:
                                    url = "http://vorud.medad-art.ir//from-date-information"
                                    p_id = request.user.employee.personelnumber
                                    _date = report.task_time.end.replace(tzinfo=None) + datetime.timedelta(days=1)
                                    _date_str = str(_date.strftime(format="%Y/%m/%d"))
                                    payload = {'token': 'NDI5M2VjMDgxNGRmYjlhMDMwNGJmODI5NmIwZTMzYzEwMzM2YzE3NTp7Il9hdXRoX3VzZXJfaWQiOiIzIiwiX2F1dGhfdXNlcl9iYWNrZW5kIjoiZ', 'i_date': _date_str, 'p_id': p_id}
                                    files = []
                                    headers= {}

                                    response = requests.request("POST", url, headers=headers, data = payload, files = files)
                                    response_time = datetime.datetime.strptime(response.text[:19], '%Y-%m-%d %H:%M:%S')
                                    if (datetime.datetime.now() - response_time).total_seconds() > (SystemPublicSetting.objects.first().writing_telework_reports_limit_days * 24 +5) * 3600:
                                        context["Error"] = "فرصت ثبت گزارش برای زمان مد نظر شما تمام شده است"
                                        context['report_content'] = request.POST["content"]
                                        context["Status"]="Error"
                                        return render(request, 'time/add.html', {'context':context})
                                except:
                                    pass
                            ############################## notification
                            #delete time notification
                            if report.task_time.tasktime_notification:
                                notification=Notification.objects.get(pk=report.task_time.tasktime_notification.pk)
                                notification.closed=True
                                notification.save()


                            report.save()

                            # if report type is not common report or result or event . it can have some extensions based on its type
                            if report.report_type > 3:
                                try:
                                    _extension = report.extension
                                except:
                                    _extension = ReportExtension()
                                    _extension.report = report
                                
                                context["ext_direction"] = bool(int(request.POST["report_body_extension_direction_input"]))
                                _extension.target_started = context["ext_direction"]
                                context["ext_success"] = bool(int(request.POST["report_body_extension_success_input"]))
                                _extension.succeed = context["ext_success"]
                                context["ext_score"] = int(request.POST["report_body_extension_score_input"])
                                _extension.enhancement_score = context["ext_score"]
                                context["ext_malicious"] = bool(int(request.POST["report_body_extension_malicious_input"]))
                                _extension.malicious_file_link = context["ext_malicious"]
                                context["ext_summary"] = request.POST["report_body_extension_link_summary"]
                                _extension.chat_summary = context["ext_summary"] 
                                context["ext_link_addr"] = request.POST["report_body_extension_link_addr_input"]
                                _extension.link_address = context["ext_link_addr"]
                                context["ext_link_agent"] = request.POST["report_body_extension_link_agent_input"]
                                _extension.link_user_agent = context["ext_link_agent"]
                                context["ext_malware"] = request.POST["report_body_extension_malware_input"]
                                _extension.malware_type = context["ext_malware"]
                                context["ext_file_type"] = request.POST["report_body_extension_file_type_input"]
                                _extension.file_type = context["ext_file_type"]
                                
                                _extension.save()

                            # report tags
                            if "report_tag" in request.POST:
                                _tags=request.POST["report_tag"].split(",")
                                for t in _tags:
                                    report.tags.add(t)
                                # in edit mood if tags had been edited
                                if (time_id and report_id):
                                    for t in report.tags.all():
                                        if t.name not in _tags:
                                            report.tags.remove(t.name)
                                    context["report_tags"]=request.POST["report_tag"]
                                else:
                                    context["report_tags"]=''
                            report.save() 
                            
                            ###################### save report attachments ########
                            if request.FILES:
                                files = request.FILES
                                for i in files:
                                    j = files[i]
                                    report_attachment = ReportAttachment()
                                    report_attachment.name = j.name
                                    report_attachment.report=report
                                    report_attachment.attachment_file = j
                                    report_attachment.filename = j.name
                                    report_attachment.save()
                            # send notification to manager for confirm report
                            if report.task_time.user.employee.GetEmployeeParent:
                                parent=User.objects.get(pk=report.task_time.user.employee.GetEmployeeParent)
                                notification=Notification()
                                if report.confirmed_notification:
                                    notification=report.confirmed_notification
                                notification.title="گزارش تائید نشده"
                                notification.user=parent
                                # notification will display to manager after 2 days
                                notification.displaytime=report.created + datetime.timedelta(days=2)
                                notification.messages=report.task_time.user.first_name+" "+report.task_time.user.last_name +" در تاریخ "+ConvertToSolarDate(task_time.start) + " گزارش تائید نشده دارد. "
                                report.save()
                                notification.link="/report/list/?r_id=" +str(report.id)  
                                notification.save()
                                report.confirmed_notification=notification
                                ############################## notification
                                if not report_id and "time_add_report_add_type" in request.POST and request.POST["time_add_report_add_type"]=="draft":
                                    report.draft=True
                                else:
                                    report.draft=False
                                report.save()
                                this_report_id=report.id
                                # if report is draft this messege is displayed
                                if not report_id and "time_add_report_add_type" in request.POST and request.POST["time_add_report_add_type"]=="draft":
                                    context["Message"]="ذخیره پیش نویس با موفقیت انجام شد"
                                # if report is not drdaft this messege is displayed
                                else:
                                    context["Message"]=" گزارش با موفقیت ذخیره شد"
                                
                                if (time_id and report_id):
                                    context["report_id"]=report.id
                                    context["time_id"]=task_time.id
                                    context["mode"]='TimeAndReportEdit'
                                else:
                                    context["report_id"]=0
                                    context["time_id"]=0
                                    context["mode"]='NewAll'
                            context["Status"]="Saved"
                            
                            task_time.TimeLineColorUpdate()
                        except Exception as ex:
                            context['report_content'] = request.POST["content"]
                            context["Error"] = ex.args[0]
                            context["Status"]="Error"
            
            # for public task, if this task type exists
            elif request.POST["time_add_task_kind"]=="public":
                public_task_time=PublicTaskTime()
                public_task_time.user=request.user
                #---------------------------------------
                _public_task_key = int(request.POST["time_add_task_key"])
                public_task=PublicTask.objects.get(pk=_public_task_key)
                public_task_time.public_task=public_task
                #---------------------------------------
                public_task_time.start=start_date_time
                public_task_time.end=end_date_time
                #---------------------------------------
                public_task_time.save()
                context["Status"]="Saved"
                context["time_id"]=public_task_time.pk
                return render(request, 'time/add.html', {'context':context})
            else:
                context["Error"] = "ذخیره با خطا روبرو شد."
                context['report_content'] = request.POST["content"]
                context["Status"]="Error"
                return render(request, 'time/add.html', {'context':context})
        except Exception as ex:
            context['report_content'] = request.POST["content"]
            context["Error"] = ex.args[0]
            context["Status"]="Error"
       
    return render(request, 'time/add.html', {'context':context})

# function to get all task times in a month
@login_required(login_url='user:login') #redirect when user is not logged in
def GetMonthDays(request,year,month):
    month_days={}
    
    _today = ConvertToSolarDate(str(datetime.date.today()))

    # find first day in month
    _first_date_time_in_month=datetime.datetime.strptime(ConvertToMiladi(str(year)+"/"+str(month)+"/1")+" 00:00:00",'%Y-%m-%d %H:%M:%S')
    month_days["1"]=([ConvertToSolarDate(_first_date_time_in_month),GetWeekDay(_first_date_time_in_month),_today])
    for i in range(2,32):
        _first_date_time_in_month+=datetime.timedelta(days=1)
        if str(ConvertToSolarDate(_first_date_time_in_month).split("/")[1])==str(month):
            #create a dictionary with key of month days and value of date and weekday of that
            month_days[str(i)]=([ConvertToSolarDate(_first_date_time_in_month),GetWeekDay(_first_date_time_in_month),_today])
    
    return  JsonResponse(month_days)

@login_required(login_url='user:login') #redirect when user is not logged in
def GetTrafficsDays(request,user_id,year,month):
    

    _date=jdt(year=int(year), month=int(month), day=1)

    _user=None
    if user_id:
        _user=user_id
    else:
        _user=request.user.id
    this_user=User.objects.get(pk=_user)

    if _user !=request.user.id and request.user.id not in this_user.employee.GetEmployeeParentSet and request.user.id not in this_user.employee.GetEmployeeParentLocumtenensSet:
        raise PermissionDenied

    p_id = this_user.employee.personelnumber

    url = "http://vorud.medad-art.ir//daily-information"


    _date_str = str(_date.strftime(format="%Y/%m/%d"))
    payload = {'token': 'NDI5M2VjMDgxNGRmYjlhMDMwNGJmODI5NmIwZTMzYzEwMzM2YzE3NTp7Il9hdXRoX3VzZXJfaWQiOiIzIiwiX2F1dGhfdXNlcl9iYWNrZW5kIjoiZ', 'i_date': _date_str, 'p_id': p_id}
    files = []
    headers= {}

    response = requests.request("POST", url, headers=headers, data = payload, files = files)

    return JsonResponse(response.text.replace('/0','/',60), safe=False)

@login_required(login_url='user:login') #redirect when user is not logged in
def GetMonthTrafficsDays(request,user_id,year,month):
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

    _date = jdt(year=int(year), month=int(month), day=1)
    this_user=User.objects.get(pk=_user)
    if _user != as_user.id and as_user.id not in this_user.employee.GetEmployeeParentSet:
        raise PermissionDenied

    p_id = this_user.employee.personelnumber

    url = "http://vorud.medad-art.ir//month-information"


    _date_str = str(_date.strftime(format="%Y/%m/%d"))
    payload = {'token': 'NDI5M2VjMDgxNGRmYjlhMDMwNGJmODI5NmIwZTMzYzEwMzM2YzE3NTp7Il9hdXRoX3VzZXJfaWQiOiIzIiwiX2F1dGhfdXNlcl9iYWNrZW5kIjoiZ', 'i_date': _date_str, 'p_id': p_id}
    files = []
    headers= {}

    response = requests.request("POST", url, headers=headers, data = payload, files = files)

    return JsonResponse(response.text.replace('/0','/',60), safe=False)


@login_required(login_url='user:login') #redirect when user is not logged in
def GetTimesDays(request,user_id,year,month):
    color_list=['red','lightsalmon','#4ae899','gray']
    
    times_data={}
    _first_date_time_in_month=datetime.datetime.strptime(ConvertToMiladi(str(year)+"/"+str(month)+"/1")+" 00:00:00",'%Y-%m-%d %H:%M:%S')
    _last_date_time_in_month=datetime.datetime.strptime(ConvertToMiladi(str(year)+"/"+str(month)+"/1")+" 23:59:00",'%Y-%m-%d %H:%M:%S')
    for i in range(2,32):
        _last_date_time_in_month+=datetime.timedelta(days=1)
        if str(ConvertToSolarDate(_last_date_time_in_month).split("/")[1])!=str(month):
            _last_date_time_in_month-=datetime.timedelta(days=1)
    

    _user=None
    if user_id:
        _user=user_id
    else:
        _user=request.user.id

    this_user=User.objects.get(pk=_user)
    if _user !=request.user.id and request.user.id not in this_user.employee.GetEmployeeParentSet and request.user.id not in this_user.employee.GetEmployeeParentLocumtenensSet:
        raise PermissionDenied

    _task_times=TaskTime.objects.filter(user__id=_user).filter(
        Q(start__gte=_first_date_time_in_month,start__lte=_last_date_time_in_month,end__gte=_first_date_time_in_month,end__lte=_last_date_time_in_month)
        |Q(start__lte=_first_date_time_in_month,end__gte=_first_date_time_in_month)
        |Q(start__lte=_last_date_time_in_month,end__gte=_last_date_time_in_month)).annotate(type=Value("private",CharField()))

    #start__gte=_first_date_time_in_month,start__lte=_last_date_time_in_month,end__gte=_first_date_time_in_month,end__lte=_last_date_time_in_month,


    #----------------------------------------------------public_task_time
    _public_task_times=PublicTaskTime.objects.filter(user__id=_user).filter(
        Q(start__gte=_first_date_time_in_month,start__lte=_last_date_time_in_month,end__gte=_first_date_time_in_month,end__lte=_last_date_time_in_month)
        |Q(start__lte=_first_date_time_in_month,end__gte=_first_date_time_in_month)
        |Q(start__lte=_last_date_time_in_month,end__gte=_last_date_time_in_month)).annotate(color=Value(5,SmallIntegerField())).annotate(teleworking=Value(False,BooleanField())).annotate(mission=Value(False,BooleanField())).annotate(type=Value("public",CharField()))
    #start__gte=_first_date_time_in_month,start__lte=_last_date_time_in_month,end__gte=_first_date_time_in_month,end__lte=_last_date_time_in_month

    all_times=_task_times.union(_public_task_times).order_by('start','end')
    
    # creating task time graphic view for tasktimes page
    for t in all_times:
        color = ""
        row_name = ""
        task_name = ""
        time_id = 0
        if t.type == "public":
            _filtered = PublicTaskTime.objects.get(pk = t.id)
            color = 'lightblue'
            row_name = "pulick_" + str(_filtered.id)
            task_name = _filtered.TaskName
            time_id = _filtered.id
        else:
            _filtered = TaskTime.objects.get(pk = t.id)
            color = color_list[_filtered.color]
            row_name = "private_"+str(_filtered.id)
            task_name = _filtered.TaskName
            time_id = t.id

        time_start_date = ConvertToSolarDate(t.start)
        time_end_date = ConvertToSolarDate(t.end)
        # seperate clock part of time 
        time_start = str(t.start)[11:16]
        time_end = str(t.end)[11:16]
        
        if time_start_date == time_end_date:
            left = (int(time_start[0:2])*60+int(time_start[3:5]))/1440*100
            width = (int(time_end[0:2])*60+int(time_end[3:5]))/1440*100-left
            right = left-100+width
            times_data[row_name] = [time_start_date,time_start,time_end,right,width,color,task_name,time_id,t.type,t.teleworking , t.mission]
        else:
            _first = datetime.datetime.strptime(ConvertToMiladi(time_start_date)+" "+time_start+":00",'%Y-%m-%d %H:%M:%S')
            _end = datetime.datetime.strptime(ConvertToMiladi(time_end_date)+" "+time_end + ":00",'%Y-%m-%d %H:%M:%S')
            left = (int(time_start[0:2])*60+int(time_start[3:5]))/1440*100
            width = (23*60+59)/1440*100-left
            right = left-100+width
            _row_name = row_name+"_1"
            times_data[_row_name] = [time_start_date,time_start,"23:59",right,width,color,task_name,time_id,t.type,t.teleworking , t.mission]
            _row_number = 1
            _first += datetime.timedelta(days = 1)
            time_start_date = ConvertToSolarDate(str(_first))
            time_end_date = ConvertToSolarDate(str(_end))
            while(time_start_date != time_end_date):
                _row_number += 1
                _row_name = row_name+"_"+str(_row_number)
                time_start = '00:00'
                time_end = '23:59'
                left = (int(time_start[0:2])*60+int(time_start[3:5]))/1440*100
                width = (int(time_end[0:2])*60+int(time_end[3:5]))/1440*100-left
                right = left-100+width
                times_data[_row_name] = [time_start_date,time_start,time_end,right,width,color,task_name,time_id,t.type,t.teleworking , t.mission]
                _first += datetime.timedelta(days=1)
                time_start_date = ConvertToSolarDate(str(_first))
                time_end_date = ConvertToSolarDate(str(_end))
            _row_number += 1
            _row_name = row_name+"_"+str(_row_number)
            time_start = '00:00'
            time_end = str(_end)[11:16]
            left = (int(time_start[0:2])*60+int(time_start[3:5]))/1440*100
            width = (int(time_end[0:2])*60+int(time_end[3:5]))/1440*100-left
            right = left-100+width
            times_data[_row_name] = [time_start_date,time_start,time_end,right,width,color,task_name,time_id,t.type,t.teleworking , t.mission]
    return  JsonResponse(times_data)


@login_required(login_url='user:login') #redirect when user is not logged in
def TimeList(request):
    request.session["activated_menu"]="times_list"
    context={}
    _date_time_now=datetime.datetime.now()
    context["time_list_this_year"]=int(ConvertToSolarDate(_date_time_now).split("/")[0])
    context["time_list_this_year_range"]=range(1390,int(ConvertToSolarDate(_date_time_now).split("/")[0])+1)
    context["time_list_this_month"]=int(ConvertToSolarDate(_date_time_now).split("/")[1])

    context["isManager"]=False
    context["children_user"]=None
    if(request.user.employee.organization_group.manager==request.user):
        context["isManager"]=True
        context["children_user"]=User.objects.filter(is_active=True).filter(pk__in=request.user.employee.GetAllChildrenUserId).order_by("last_name")
    
    if len(request.user.locumtenens_organization_groups.all())>0 and request.user.locumtenens_organization_groups.first().locumtenens_active :
        context["isManager"]=True
        context["children_user"]=User.objects.filter(is_active=True).filter(pk__in=request.user.locumtenens_organization_groups.first().manager.employee.GetAllChildrenUserId).exclude(id=request.user.id).order_by("last_name")
    
    return render(request, 'time/list.html', {'context':context})

@login_required(login_url='user:login') #redirect when user is not logged in
def StartTaskTime(request,task_id,kind):
    try:
        temp_timing_record=TempTimingRecord()
        temp_timing_record.user=request.user
        temp_timing_record.start=datetime.datetime.now()
        if(kind==1):
            _public_task=PublicTask.objects.get(pk=task_id)
            temp_timing_record.public_task=_public_task
            
        else:
            _task=Task.objects.get(pk=task_id)
            _user = request.user
            if (_task.user_assignee == _user) or _task.public  or (_task.group_assignee.head == _user) :
                temp_timing_record.task = _task
            
            else:
                raise PermissionDenied
        temp_timing_record.save()
        
        return HttpResponse(True)
    except Exception as err:
       return  HttpResponse(err.args[0])

@login_required(login_url='user:login') #redirect when user is not logged in
def CancelTaskTime(request):
    try:
        temp_timing_record=TempTimingRecord.objects.get(user=request.user)
        temp_timing_record.delete()

        return HttpResponse(True)
    except Exception as err:
        return  HttpResponse(err.args[0])


@login_required(login_url='user:login') #redirect when user is not logged in
def GetTaskTime(request):
    temp_timing_record=TempTimingRecord.objects.filter(user=request.user)
    data={}
    try:
        if (len(temp_timing_record)>0):
            _start_date_time=temp_timing_record[0].start.replace(tzinfo=None)
            data["timer"]=(ConvertTimeDeltaToStringTime(DateTimeDifference(_start_date_time,datetime.datetime.now())))
            data["description"]=temp_timing_record[0].description
            if(temp_timing_record[0].task):
                data["task_name"]=temp_timing_record[0].task.name
                data["task_id"]=temp_timing_record[0].task.id
                data["task_type"]='private'
            else:
                data["task_name"]=temp_timing_record[0].public_task.name
                data["task_id"]=temp_timing_record[0].public_task.id
                data["task_type"]='public'
        else:
            data["timer"]="00:00:00"
            data["task_name"]="انتخاب کار جاری"
            data["task_id"]='0'
            data["task_type"]=''
        
        return  JsonResponse(data)

    except Exception as err:
        return  HttpResponse(err.args[0])


@login_required(login_url='user:login') #redirect when user is not logged in
def ConfirmTaskTime(request):
    temp_timing_record=TempTimingRecord.objects.get(user=request.user)
    try:
        result={}
        result["report_id"]=0
        if (datetime.datetime.now() - temp_timing_record.start.replace(tzinfo=None)).total_seconds() < 600:
            result["status"]=False
            return  JsonResponse(result)

        if(temp_timing_record.start.date() != datetime.datetime.now().date()):
            result["status"]="day_error"
            return  JsonResponse(result)                

        _user = request.user
        start_date_time = temp_timing_record.start
        end_date_time = datetime.datetime.now()

        task_time=TaskTime.objects.filter(Q(start__lte = start_date_time,end__gte = end_date_time,user =_user )\
            |Q(start__lte = start_date_time,end__gt = start_date_time,user =_user )\
                |Q(start__lt = end_date_time,end__gte = end_date_time,user =_user )\
                    |Q(start__gte = start_date_time,end__lte = end_date_time,user =_user)\
                        |Q(start__lte = start_date_time,end__gte = end_date_time,user =_user )\
                            |Q(start__lte = start_date_time,end__gt = start_date_time,user =_user )\
                                |Q(start__lt = end_date_time,end__gte = end_date_time,user =_user )\
                                    |Q(start__gte = start_date_time,end__lte = end_date_time,user =_user)\
                                        )
        if(task_time):
            result["status"]="conflict_error"
            return  JsonResponse(result)    

        if temp_timing_record.public_task:
            public_task_time=PublicTaskTime()
            public_task_time.public_task=temp_timing_record.public_task
            public_task_time.user=request.user
            public_task_time.start=temp_timing_record.start
            public_task_time.end=datetime.datetime.now()
            public_task_time.save()
            temp_timing_record.delete()

            result["status"]=True
            result["id"]=public_task_time.id
            return  JsonResponse(result)

        elif temp_timing_record.task:
            task_time=TaskTime()
            task_time.task=temp_timing_record.task
            task_time.user=request.user
            task_time.start=temp_timing_record.start
            task_time.end=datetime.datetime.now()
            task_time.save()
            if temp_timing_record.description and temp_timing_record.description !="":
                report=Report()
                report.title="پیش نویس"
                report.content=temp_timing_record.description
                report.task_time=task_time
                report.draft=True
                report.save()
                result["report_id"]=report.pk
            else:
                ############################## notification
                notification=Notification()
                notification.title="ثبت گزارش"
                notification.user=task_time.user
                notification.displaytime=datetime.datetime.now() + datetime.timedelta(days=1)
                notification.messages=" برای کار "+task_time.task.name+" ساعت بدون گزارش ثبت شده است "
                notification.link="/report/None/time/"+str(task_time.pk)+"/private/add/"
                notification.save()

                task_time.tasktime_notification=notification
                task_time.save()
                ############################## notification
            
            temp_timing_record.delete()
            result["status"]=True
            result["id"]=task_time.id
            return  JsonResponse(result)
    except Exception as err:
        return  HttpResponse(err.args[0])

@login_required(login_url='user:login') #redirect when user is not logged in
def GetTimeReports(request,time_id):
    data={}
    task_time=TaskTime.objects.get(pk=time_id)
    if len(request.user.locumtenens_organization_groups.all())>0 and request.user.locumtenens_organization_groups.first().locumtenens_active:
        if task_time.user.id !=request.user.locumtenens_organization_groups.first().manager.id and request.user.locumtenens_organization_groups.first().manager.id not in task_time.user.employee.GetEmployeeParentSet :
            raise PermissionDenied
    else:
        if task_time.user.id !=request.user.id and request.user.id not in task_time.user.employee.GetEmployeeParentSet :
            raise PermissionDenied
    reports=ReportSerializer(Report.objects.filter(task_time__id=int(time_id)), many=True)
    data["reports"]=JSONRenderer().render(reports.data).decode("utf-8")   
    return  JsonResponse(data)



@login_required(login_url='user:login') #redirect when user is not logged in
def GetTaskTimeDetail(request,time_id,kind):
    context={}
    if kind=="private":
        try:
            task_time=TaskTime.objects.get(pk=time_id)
            if len(request.user.locumtenens_organization_groups.all())>0 and request.user.locumtenens_organization_groups.first().locumtenens_active:
                if task_time.user.id !=request.user.locumtenens_organization_groups.first().manager.id and request.user.locumtenens_organization_groups.first().manager.id not in task_time.user.employee.GetEmployeeParentSet :
                    raise PermissionDenied
            else:
                if task_time.user.id !=request.user.id and request.user.id not in task_time.user.employee.GetEmployeeParentSet :
                    raise PermissionDenied
            context["task_name"] = task_time.task.name
            context["time_key"]=time_id
            context["time_task_kind"]="private"
            context["time_start_date"]=ConvertToSolarDate(task_time.start)
            context["time_end_date"]=ConvertToSolarDate(task_time.end)
            context["time_start"]=str(task_time.start)[11:16]
            context["time_end"]=str(task_time.end)[11:16]
            context["mission"] = task_time.mission
            context["teleworking"] = task_time.teleworking
        except:
            return JsonResponse({})
    else:
        try:
            task_time=PublicTaskTime.objects.get(pk=time_id)
            if len(request.user.locumtenens_organization_groups.all())>0 and request.user.locumtenens_organization_groups.first().locumtenens_active:
                if task_time.user.id !=request.user.locumtenens_organization_groups.first().manager.id and request.user.locumtenens_organization_groups.first().manager.id not in task_time.user.employee.GetEmployeeParentSet :
                    raise PermissionDenied
            else:
                if task_time.user.id !=request.user.id and request.user.id not in task_time.user.employee.GetEmployeeParentSet :
                    raise PermissionDenied
            context["task_name"]=task_time.public_task.name
            context["time_key"]=time_id
            context["time_task_kind"]="public"
            context["time_start_date"]=ConvertToSolarDate(task_time.start)
            context["time_end_date"]=ConvertToSolarDate(task_time.end)
            context["time_start"]=str(task_time.start)[11:16]
            context["time_end"]=str(task_time.end)[11:16]
            context["mission"] = task_time.mission
            context["teleworking"] = task_time.teleworking
        except:
            return JsonResponse({})
    return JsonResponse(context)

# function for edit task time detail 
@login_required(login_url='user:login') #redirect when user is not logged in
def EditTaskTimeDetail(request):
    context={}
    context['success'] = False
    if request.method == "POST":
        try:
            # task time edit conditions
            this_task_time_id=int(request.POST["time_edit_task_key"])
            start_date_time=datetime.datetime.strptime(ConvertToMiladi(str(request.POST["time_edit_start_date"]))+" "+str(request.POST["time_start"])+":00",'%Y-%m-%d %H:%M:%S')
            end_date_time=datetime.datetime.strptime(ConvertToMiladi(str(request.POST["time_edit_start_date"]))+" "+str(request.POST["time_end"])+":00",'%Y-%m-%d %H:%M:%S')
            # if(start_date_time.date() != end_date_time.date()):
            #     context["message"] = "امکان ثبت ساعت فراتر از یک روز وجود ندارد"
            #     return JsonResponse(context)
            
            if (start_date_time>=end_date_time):
                context["message"] = "زمان پایان باید بزرگتر از زمان شروع باشد"
                return JsonResponse(context)
            _user = request.user
            task_time_1=TaskTime.objects.filter(start__lte = start_date_time).filter(end__gte = end_date_time).filter(user =_user ).exclude(pk=this_task_time_id)
            if(task_time_1):
                context["message"] = "زمان وارد شده با زمان های  قبل تداخل دارد"
                return JsonResponse(context)  
            task_time_2=TaskTime.objects.filter(start__lte = start_date_time).filter(end__gt = start_date_time).filter(user =_user ).exclude(pk=this_task_time_id)
            if(task_time_2):
                context["message"] = "زمان وارد شده با زمان های  قبل تداخل دارد"
                return JsonResponse(context) 
            task_time_3=TaskTime.objects.filter(start__lt = end_date_time).filter(end__gte = end_date_time).filter(user =_user ).exclude(pk=this_task_time_id)
            if(task_time_3):
                context["message"] = "زمان وارد شده با زمان های  قبل تداخل دارد"
                return JsonResponse(context)  
            task_time_4=TaskTime.objects.filter(start__gte = start_date_time).filter(end__lte = end_date_time).filter(user =_user ).exclude(pk=this_task_time_id)
            if(task_time_4):
                context["message"] = "زمان وارد شده با زمان های  قبل تداخل دارد"
                return JsonResponse(context)

            task_time_5=PublicTaskTime.objects.filter(start__lte = start_date_time).filter(end__gte = end_date_time).filter(user =_user ).exclude(pk=this_task_time_id)
            if(task_time_5):
                context["message"] = "زمان وارد شده با زمان های  قبل تداخل دارد"
                return JsonResponse(context) 
            task_time_6=PublicTaskTime.objects.filter(start__lte = start_date_time).filter(end__gt = start_date_time).filter(user =_user ).exclude(pk=this_task_time_id)
            if(task_time_6):
                context["message"] = "زمان وارد شده با زمان های  قبل تداخل دارد"
                return JsonResponse(context)
            task_time_7=PublicTaskTime.objects.filter(start__lt = end_date_time).filter(end__gte = end_date_time).filter(user =_user ).exclude(pk=this_task_time_id)
            if(task_time_7):
                context["message"] = "زمان وارد شده با زمان های  قبل تداخل دارد"
                return JsonResponse(context)  
            task_time_8=PublicTaskTime.objects.filter(start__gte = start_date_time).filter(end__lte = end_date_time).filter(user =_user).exclude(pk=this_task_time_id)
            if(task_time_8):
                context["message"] = "زمان وارد شده با زمان های  قبل تداخل دارد"
                return JsonResponse(context)

            if (end_date_time - start_date_time).total_seconds() < 600:
                context["message"] = "زمان وارد شده حداقل باید 10 دقیقه باشد"
                return JsonResponse(context)

            if (datetime.datetime.now() - end_date_time).total_seconds() < 0:
                context["message"] = "امکان ثبت گزارش برای آینده وجود ندارد"
                return JsonResponse(context)


            if request.POST["time_edit_task_kind"]=="private":
                task_time=TaskTime.objects.get(pk=int(request.POST["time_edit_task_key"]))
                task_time.teleworking = "time_edit_teleworking_checkbox" in request.POST
                task_time.mission = "time_edit_mission_checkbox" in request.POST

                if SystemPublicSetting.objects.first() and SystemPublicSetting.objects.first().writing_reports_limit_days > 0 and not task_time.teleworking:
                    if (datetime.datetime.now() - end_date_time).total_seconds() > (SystemPublicSetting.objects.first().writing_reports_limit_days * 24 + 5) * 3600:
                        context["message"] =  "فرصت ثبت کارکرد برای زمان مد نظر شما تمام شده است"
                        return JsonResponse(context)

                # get entrance and exit information from vorud site
                if SystemPublicSetting.objects.first() and SystemPublicSetting.objects.first().writing_telework_reports_limit_days > 0 and task_time.teleworking:
                    try:
                        url = "http://vorud.medad-art.ir//from-date-information"
                        p_id = request.user.employee.personelnumber
                        _date = end_date_time + datetime.timedelta(days=1)
                        _date_str = str(_date.strftime(format="%Y/%m/%d"))
                        payload = {'token': 'NDI5M2VjMDgxNGRmYjlhMDMwNGJmODI5NmIwZTMzYzEwMzM2YzE3NTp7Il9hdXRoX3VzZXJfaWQiOiIzIiwiX2F1dGhfdXNlcl9iYWNrZW5kIjoiZ', 'i_date': _date_str, 'p_id': p_id}
                        files = []
                        headers= {}

                        response = requests.request("POST", url, headers=headers, data = payload, files = files)
                        response_time = datetime.datetime.strptime(response.text[:19], '%Y-%m-%d %H:%M:%S')
                        if (datetime.datetime.now() - response_time).total_seconds() > (SystemPublicSetting.objects.first().writing_telework_reports_limit_days * 24 + 5) * 3600:
                            context["message"] =  "فرصت ثبت کارکرد برای زمان مد نظر شما تمام شده است"
                            return JsonResponse(context)
                    except:
                        pass

                reports=Report.objects.filter(task_time=task_time,confirmed=True)
                if (len(reports)>0):
                    context["message"]="خطا در ویرایش اطلاعات"
                    return JsonResponse(context)
                #----------------- Access Control ------
                if task_time.user.id !=request.user.id :
                    raise PermissionDenied
                #---------------------------------------
                task_time.start=start_date_time
                task_time.end=end_date_time
                #---------------------------------------
                task_time.save()
                reports=Report.objects.filter(task_time=task_time)
                for report in reports:
                    try:
                        notification=report.confirmed_notification
                        notification.displaytime=report.created + datetime.timedelta(days=2)
                        notification.messages=task_time.user.first_name+" "+task_time.user.last_name +" در تاریخ "+ConvertToSolarDate(task_time.start) + " گزارش تائید نشده دارد. "
                        notification.save()
                    except:
                        pass

                context["message"]="ویرایش ساعت با موفقیت انجام شد"
                context['success']=True
        
                return JsonResponse(context)

            elif request.POST["time_edit_task_kind"]=="public":
                public_task_time=PublicTaskTime.objects.get(pk=int(request.POST["time_edit_task_key"]))
                #----------------- Access Control ------
                if public_task_time.user.id !=request.user.id :
                    raise PermissionDenied
                #---------------------------------------
                #---------------------------------------
                public_task_time.start=start_date_time
                public_task_time.end=end_date_time
                #---------------------------------------
                public_task_time.save()
                context["message"]="ویرایش ساعت با موفقیت انجام شد"
                return JsonResponse(context)
        except:
            pass

    context["message"]="خطا در ویرایش اطلاعات"
    return JsonResponse(context)


# function for delete a task time with all of its reports
@login_required(login_url='user:login') #redirect when user is not logged in
def DeleteTimeWithReports(request,time_id,kind):
    if kind=="private":
        try:
            task_time=TaskTime.objects.get(pk=time_id)
            #----------------- Access Control ------
            if task_time.user.id !=request.user.id :
                raise PermissionDenied
            #---------------------------------------
            try:
                # if task time has a notification, it will be deleted.
                notification = task_time.tasktime_notification
                notification.delete()
            except:
                pass
            reports=Report.objects.filter(task_time=task_time)
            for report in reports:
                try:
                    notification=report.confirmed_notification
                    notification.delete()
                except:
                    pass
            task_time.delete()
            return HttpResponse("True")
        except:
            return HttpResponse("False")
    else:
        try:
            task_time=PublicTaskTime.objects.get(pk=time_id)
            #----------------- Access Control ------
            if task_time.user.id !=request.user.id :
                raise PermissionDenied
            #---------------------------------------
            task_time.delete()
            return HttpResponse("True")
        except:
            return HttpResponse("False")
    return HttpResponse("False")

# Draft for private task 
@login_required(login_url='user:login') #redirect when user is not logged in
def SetTempTaskTimeDescription(request):
    try:
        temp_timing_record=TempTimingRecord.objects.get(user=request.user)
        temp_timing_record.description=request.POST["description"]
        
        temp_timing_record.save()
        
        return HttpResponse(True)
    except Exception as err:
       return  HttpResponse(err.args[0])

# get task times in a day 
@login_required(login_url='user:login') #redirect when user is not logged in
def GetTimesInDay(request,year,month,day,**kwargs):
    user_id=kwargs.get('user_id',None)
    if user_id:
        _user=user_id
    else:
        _user=request.user.id

    this_user=User.objects.get(pk=_user)
    if _user !=request.user.id and request.user.id not in this_user.employee.GetEmployeeParentSet:
        raise PermissionDenied
    
    # color list for task_time types 
    color_list=['red','lightsalmon','lightgreen','gray']

    times_data={}
    data = {}

    # start and end of specified date
    day_start = datetime.datetime.strptime(ConvertToMiladi(str(year)+"/"+str(month)+"/"+str(day))+" 00:00:00",'%Y-%m-%d %H:%M:%S')
    day_end = datetime.datetime.strptime(ConvertToMiladi(str(year)+"/"+str(month)+"/"+str(day))+" 23:59:59",'%Y-%m-%d %H:%M:%S')
    _today = str(year)+"/"+str(month)+"/"+str(day)

    _week_day=GetWeekDay(day_start)
    data["weekday"] = _week_day

    # task times
    _task_times=TaskTime.objects.filter(user=this_user).exclude(start__gte = day_end).exclude(end__lte = day_start).annotate(type=Value("private",CharField()))
    #----------------------------------------------------public_task_time
    _public_task_times=PublicTaskTime.objects.filter(user=this_user).exclude(start__gte = day_end ).exclude( end__lte = day_start).annotate(color=Value(5,SmallIntegerField())).annotate(teleworking=Value(False,BooleanField())).annotate(mission=Value(False,BooleanField())).annotate(type=Value("public",CharField()))

    all_times=_task_times.union(_public_task_times).order_by('start','end')

    # push some data about task time in time_data .
    for t in all_times:
        color=""
        row_name=""
        task_name=""
        time_id=0
        # set task time attribute
        if t.type=="public":
            _filtered=PublicTaskTime.objects.get(pk=t.id)
            color='lightblue'
            row_name="pulick_"+str(_filtered.id)
            task_name=_filtered.TaskName
            time_id=_filtered.id
        else:
            _filtered=TaskTime.objects.get(pk=t.id)
            color=color_list[_filtered.color]
            row_name="private_"+str(_filtered.id)
            task_name=_filtered.TaskName
            time_id=t.id

        time_start_date=ConvertToSolarDate(t.start)
        time_end_date=ConvertToSolarDate(t.end)
        # to seperate time and date. because we just want time.
        time_start=str(t.start)[11:16]
        time_end=str(t.end)[11:16]

        if time_start_date==time_end_date:
            # finds task time length shown in add task time page
            left=(int(time_start[0:2])*60+int(time_start[3:5]))/1440*100
            width=(int(time_end[0:2])*60+int(time_end[3:5]))/1440*100-left
            right=left-100+width
            # row_name is "private_"+task_id or "public_"+task_id
            times_data[row_name]=[time_start_date,time_start,time_end,right,width,color,task_name,time_id,t.type,t.teleworking , t.mission]
        else:
            # if a task time range be out of a day this section will be run 
            _first=datetime.datetime.strptime(ConvertToMiladi(time_start_date)+" "+time_start+":00",'%Y-%m-%d %H:%M:%S')
            _end=datetime.datetime.strptime(ConvertToMiladi(time_end_date)+" "+time_end + ":00",'%Y-%m-%d %H:%M:%S')
            today_first = datetime.datetime.strptime(ConvertToMiladi(_today)+" 00:00:00",'%Y-%m-%d %H:%M:%S')
            today_end = datetime.datetime.strptime(ConvertToMiladi(_today)+" 23:59:00",'%Y-%m-%d %H:%M:%S')
            
            # if task time starts befor than today we set start of shown task-time 00:00
            if today_first > _first:
                time_start = "00:00"
            # if task time ends after than today we set end of shown task-time 23:59
            if today_end < _end : 
                time_end = "23:59"

            # finds task time length shown in add task time page
            left=(int(time_start[0:2])*60+int(time_start[3:5]))/1440*100
            width=(int(time_end[0:2])*60+int(time_end[3:5]))/1440*100-left
            right=left-100+width
            times_data[row_name]=[_today,time_start,time_end,right,width,color,task_name,time_id,t.type,t.teleworking , t.mission]
    
    data["times_data"]=times_data
    return  JsonResponse(data)

@transaction.atomic
def AddTimeAndReport(task, start, end, report_text):
    _task = Task.objects.get(pk = task)
    if _task.user_assignee:
        _user = _task.user_assignee
    elif _task.group_assignee:
        _user = _task.group_assignee.head
    else:
        return "کار مورد نظر فاقد مسئول می باشد"

    if start == None:
        return "فیلد تاریخ شروع باید مقدار دهی شود"
       
    else:
        start_date_time = start

    if end == None:
        return "فیلد تاریخ پایان باید مقدار دهی شود"
   
    else:
        end_date_time = end

    if(start_date_time.date() != end_date_time.date()):
        return "امکان ثبت ساعت فراتر از یک روز وجود ندارد"
        
    
    # if start time is biger than end time this error occur
    if (start_date_time>=end_date_time):
        return "زمان پایان باید بزرگتر از زمان شروع باشد"
        
    
    # this query is used for return conflicted times if exist.
    task_time=TaskTime.objects.filter(Q(start__lte = start_date_time,end__gte = end_date_time,user =_user )\
        |Q(start__lte = start_date_time,end__gt = start_date_time,user =_user )\
            |Q(start__lt = end_date_time,end__gte = end_date_time,user =_user )\
                |Q(start__gte = start_date_time,end__lte = end_date_time,user =_user)\
                    |Q(start__lte = start_date_time,end__gte = end_date_time,user =_user )\
                        |Q(start__lte = start_date_time,end__gt = start_date_time,user =_user )\
                            |Q(start__lt = end_date_time,end__gte = end_date_time,user =_user )\
                                |Q(start__gte = start_date_time,end__lte = end_date_time,user =_user)\
                                    )
    # if conflicted time exists this error occur
    if(task_time):
        return  "زمان وارد شده با زمان های  قبل تداخل دارد"
        

    # if length of time is less than 10 minute this error occur
    if (end_date_time - start_date_time).total_seconds() < 600:
        return "زمان وارد شده حداقل باید 10 دقیقه باشد"
    

    # if report time is bigger than now this error occur
    if (datetime.datetime.now() - end_date_time).total_seconds() < 0:
        return "امکان ثبت گزارش برای آینده وجود ندارد"
        
    task_time=TaskTime()
    report = Report()
    #---------------------------------------
    task_time.user=_user
    #---------------------------------------  
    task_time.task=_task
    #---------------------------------------
    task_time.start=start_date_time
    task_time.end=end_date_time
    #---------------------------------------
    task_time.save()

    if len(report_text) > 0:
        report.content = "<p>" + report_text + "</p>"
    else:
        return "امکان ثبت گزارش با متن خالی وجود ندارد"

    report.title = ''
    report.task_time=task_time
    report.save()
    report.task_time.TimeLineColorUpdate()

    notification=Notification()
    notification.title="گزارش تائید نشده"
    parent=User.objects.get(pk=report.task_time.user.employee.GetEmployeeParent)
    notification.user=parent
    # notification will display to manager after 2 days
    notification.displaytime=report.created + datetime.timedelta(days=2)
    notification.messages=report.task_time.user.first_name+" "+report.task_time.user.last_name +" در تاریخ "+ConvertToSolarDate(task_time.start) + " گزارش تائید نشده دارد. "
    
    notification.link="/report/list/?r_id=" +str(report.id)  
    notification.save()
    report.confirmed_notification=notification
    report.save()
    
    return "گزارش با موفقیت ذخیره شد"


@login_required(login_url='user:login') 
def task_time_panel(request,task_id):
    _user = request.user
    _loc_user = None
    try:
        _loc_user = request.user.locumtenens_organization_groups.first().manager
    except:
        pass
    task=Task.objects.get(pk=task_id)
    reports = Report.objects.filter(task_time__task = task).order_by('-task_time__start')[0:5]
    report_textarea = ReportContentForm()
    report_textarea.label_suffix = ""
    if task.user_assignee == _user or task.creator ==_user or (_user.id in task.creator.employee.GetEmployeeParentSet) or (task.user_assignee and _user.id in task.user_assignee.employee.GetEmployeeParentSet)or \
        task.id in request.user.employee.CopyFromAccessTasks or (_loc_user and (task.user_assignee == _loc_user or task.creator==_loc_user or (_loc_user.id in task.creator.employee.GetEmployeeParentSet) or (task.user_assignee and _loc_user.id in task.user_assignee.employee.GetEmployeeParentSet)or \
        task.id in _loc_user.employee.CopyFromAccessTasks) and len(request.user.locumtenens_organization_groups.all())>0 and \
            request.user.locumtenens_organization_groups.first().locumtenens_active) :

        return render(request, 'include/panel/task-time.html' ,{'task': task, 'reports':reports, 'report_textarea':report_textarea})
    else:
        raise PermissionDenied


@login_required(login_url='user:login') 
def single_date_timeline(request, date):
    timeline_date = datetime.datetime.strptime(date,"%Y-%m-%d").date()
    task_times = TaskTime.objects.filter(start__date = timeline_date, user=request.user).order_by('start')
    start = 6
    end = 18

    if task_times.count() :
        if task_times.first().start.time().hour < start :
            start = task_times.first().start.time().hour
        
        if task_times.last().end.time().hour + 1 > end :
            end = task_times.last().end.time().hour + 1

    task_times = task_times.annotate(left=Value(0,SmallIntegerField())).annotate(width=Value(0,SmallIntegerField()))
    for task_time in task_times:
        task_time.left = int(((end - (task_time.end.time().hour + task_time.end.time().minute / 60) ) / (end - start))*100)
        task_time.width = int((((task_time.end.time().hour + task_time.end.time().minute / 60) -  (task_time.start.time().hour + task_time.start.time().minute / 60)) / (end - start))*100)+1
    return render(request, 'time/widget/single-date-timeline.html' ,{'task_times': task_times, 'start':start, 'end':end})
