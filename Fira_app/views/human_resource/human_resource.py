from django.shortcuts import render, redirect
from django.http import HttpResponse, Http404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from ...models import Task,ResourceAssignment,Resource,TaskTime,Report , QualityOfEmployee , QualityParameter
import datetime
from ...utilities.date_tools import ConvertToMiladi, ConvertToSolarDate,DateTimeDifference,ConvertTimeDeltaToStringTime
from django.http import JsonResponse
from django.core.exceptions import PermissionDenied
from django.db.models import Q,Sum,ExpressionWrapper,F,DurationField ,Value,BooleanField
from dateutil.relativedelta import *

@login_required(login_url='user:login') #redirect when user is not logged in
def index(request):
    request.session["activated_menu"]="human_resource" 
    if (not request.user.employee.IsManager):
        return redirect("human_resource:current_user_summary_page")
    context={}
    context["start_date"]=ConvertToSolarDate(datetime.date.today()-relativedelta(months=1))
    context["end_date"]=ConvertToSolarDate(datetime.datetime.now())
    return render(request, 'human_resource/index.html', {'context':context})


@login_required(login_url='user:login') #redirect when user is not logged in
def GetUserReportData(request,start_date,end_date):
    context={}
    users=User.objects.filter(is_active=True).filter(pk__in=request.user.employee.GetAllChildrenUserId).order_by("last_name")
    
    if start_date !='None':
        _miladi_start_date_time=ConvertToMiladi(start_date.replace("-", "/"))+ " 00:00:00"
        _miladi_start_date=ConvertToMiladi(start_date.replace("-", "/"))
    else:
        _miladi_start_date_time=ConvertToMiladi('1000/00/00')+ " 00:00:00"
        _miladi_start_date=ConvertToMiladi('1000/00/00')

    if end_date !='None':
        _miladi_end_date_time=ConvertToMiladi(end_date.replace("-", "/"))+ " 23:59:59"
        _miladi_end_date=ConvertToMiladi(end_date.replace("-", "/"))
    else:
        _miladi_end_date_time=ConvertToMiladi('1999/12/30')+ " 23:59:59"
        _miladi_end_date=ConvertToMiladi('1999/12/30')
    i = 0
    for u in users:
        context[i]={}
        context[i]["pk"]=u.pk
        context[i]["name"]=u.first_name +" "+u.last_name
        
        task_time__id=[r['task_time__id'] for r in Report.objects.all().values('task_time__id')]
        task_time_duration_delta=TaskTime.objects.filter(pk__in=task_time__id, user=u,start__gte=_miladi_start_date_time,end__lte=_miladi_end_date_time).exclude(start=None,end=None).annotate(duration=ExpressionWrapper(F('end')-F('start'),output_field=DurationField())).aggregate(Sum('duration'))
        try:
            duration=ConvertTimeDeltaToStringTime(task_time_duration_delta['duration__sum'])
            context[i]['total_time_with_report']=duration
        except:
            context[i]['total_time_with_report']='00:00'
        
        task_time_with_no_report_duration_delta=TaskTime.objects.filter( user=u,start__gte=_miladi_start_date_time,end__lte=_miladi_end_date_time).exclude(pk__in=task_time__id).annotate(duration=ExpressionWrapper(F('end')-F('start'),output_field=DurationField())).aggregate(Sum('duration'))
        try:
            duration=ConvertTimeDeltaToStringTime(task_time_with_no_report_duration_delta['duration__sum'])
            context[i]['task_time_with_no_report_duration_delta']=duration
        except:
            context[i]['task_time_with_no_report_duration_delta']='00:00'
        context[i]["total_task_assign"]=Task.objects.filter(user_assignee=u,startdate__gte=_miladi_start_date,enddate__lte=_miladi_end_date).count()
        context[i]["total_task_done"]=Task.objects.filter(user_assignee=u,startdate__gte=_miladi_start_date,enddate__lte=_miladi_end_date,progress=100).count()
        context[i]["total_task_confirmed"]=Task.objects.filter(user_assignee=u,startdate__gte=_miladi_start_date,enddate__lte=_miladi_end_date,confirmed=True).count()
        context[i]["total_delayed_task"]=Task.objects.filter(user_assignee=u,startdate__gte=_miladi_start_date,enddate__lte=_miladi_end_date,progress__lt=100,enddate__lt=datetime.datetime.now()).exclude(enddate=None).count()
        if context[i]["total_task_assign"]>0 and context[i]["total_delayed_task"]>0:
            context[i]["total_delayed_task_to_all_task"]=(context[i]["total_delayed_task"]/context[i]["total_task_assign"])*100
        else:
            context[i]["total_delayed_task_to_all_task"]=0
        i += 1
    return JsonResponse(context)


@login_required(login_url='user:login') #redirect when user is not logged in
def UserSummary(request,**kwargs):
    request.session["activated_menu"]="UserSummary"
    user_id=kwargs.get('user_id',None)
    context={}
    _user=None
    if (user_id):
        _user=User.objects.get(pk=user_id)
    else:
        _user=User.objects.get(pk=request.user.id)
    
    context["user"] = _user
    context["user_summary_page_selected_user_id"] = _user.id
    
    solar_time = ConvertToSolarDate(datetime.datetime.now())
    solar_time = solar_time.split("/")
    solar_year = int(solar_time[0])
    try:
        selected_year = int(request.GET.get("year",""))
    except:
        selected_year = solar_year
    context["user_summary_page_selected_year"] = selected_year
    context["user_summary_page_year_range"] = [solar_year-3 , solar_year-2 , solar_year-1 ,  solar_year , solar_year+1 ]

    try:
        selected_month = int(request.GET.get("month",""))
    except:
        selected_month = int(solar_time[1])
    context["user_summary_page_selected_month"]= selected_month



    if request.user.id not in _user.employee.GetEmployeeParentSet and request.user!=_user:
        raise PermissionDenied
    context["selected_user"]=_user
    current_user = User.objects.get(pk=request.user.id)
    context["current_user"]  = current_user
    tasks_start=Task.started.filter(user_assignee=_user)
    context["tasks_start"]=tasks_start
    
    try:
        current_quality = QualityOfEmployee.objects.filter(user=_user).filter(year=selected_year).filter(month=selected_month)
        context["user_summary_page_quality_parameter"]=current_quality
    except:
        pass

    try:
        parameters = QualityParameter.objects.filter(group=current_user.employee.organization_group)
        context["user_summary_page_group_quality_parameter"]=parameters
    except:
        pass
    
    try:
        quality_progress_all_data = QualityOfEmployee.objects.filter(user=_user)
        quality_progress_data = dict()
        for i in quality_progress_all_data:
            key=(i.year,i.month)
            if key in quality_progress_data:
                quality_progress_data[key][0] += i.parameter.weight
                quality_progress_data[key][1] += i.value * i.parameter.weight 
            else:
                quality_progress_data[key] = [i.parameter.weight , i.value * i.parameter.weight ]
        
        quality_progress_data_list = list()
        quality_progress_data_dict = dict()
        for i in quality_progress_data:
            if i[1] < 10: 
                key_str =int(str(i[0]) +"0"+str(i[1]))
                val = quality_progress_data[i][1] / quality_progress_data[i][0]
                quality_progress_data_list.append([key_str,val])
                quality_progress_data_dict[key_str] = round(val,0)
            elif i[1]>=10 and i[1]<=12:
                key_str =int(str(i[0]) +str(i[1]))
                val = quality_progress_data[i][1] / quality_progress_data[i][0]  
                quality_progress_data_list.append([key_str,val])
                quality_progress_data_dict[key_str] = round(val,0)
            else:
                pass              
        
        quality_progress_data_list.sort()
        progress_data = dict()
        first_month = quality_progress_data_list[0][0]
        last_month = quality_progress_data_list[-1][0]
        for i in range(first_month,last_month+1,1):
            if (i % 100 <=12) and (i % 100 != 0):
                if i in quality_progress_data_dict:
                    progress_data[str(i)[:4]+"/"+str(i)[4:]] = quality_progress_data_dict[i] 
                else:
                    progress_data[str(i)[:4]+"/"+str(i)[4:]] = 1
    except:
        progress_data = {"0000/00" : "0"}
        
    context["user_summary_page_quality_progress"]= progress_data
    
    try:
        all_weight = 0
        all_score=0
        for i in current_quality:
            all_score += i.parameter.weight * i.value
            all_weight += i.parameter.weight 
        context["user_summary_page_user_quality"]= int(round(all_score /all_weight , 0))
    except:
        pass

    context["children_user"]=None
    context["isManager"]=False
    if(request.user.employee.organization_group.manager==request.user):
        context["isManager"]=True 
        _children=User.objects.filter(is_active=True).filter(pk__in=request.user.employee.GetAllChildrenUserId).annotate(DirectUser = Value(False,BooleanField())).order_by("last_name")
        _direct_children=User.objects.filter(is_active=True).filter(pk__in=request.user.employee.GetDirectChildrenUserId).order_by("last_name")
        for child in _children:
            if child in _direct_children:
                child.DirectUser=True
        context["children_user"] =_children 
    context["direct_children"] = context["current_user"].employee.GetDirectChildrenUserId

    context["parent"]=_user.employee.GetEmployeeParent
    return render(request, 'human_resource/summary.html', {'context':context})


@login_required(login_url='user:login') #redirect when user is not logged in
def AddEmployeeQuality(request,**kwargs):
    year = kwargs.get('year',None)
    month = kwargs.get('month',None)
    user_id = kwargs.get('user_id',None)
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
def GetEmployeeQuality(request,**kwargs):
    year = kwargs.get('year',None)
    month = kwargs.get('month',None)
    user_id = kwargs.get('user_id',None)
    try:
        user = User.objects.get(id=user_id)
    except:
        user = request.user
    context = {}
    score={}
    current_user = request.user
    if user_id not in current_user.employee.GetDirectChildrenUserId:
        raise PermissionDenied
    try:
        parameters = QualityParameter.objects.filter(group=current_user.employee.organization_group)
        parameters_name=[]
        for i in parameters:
            parameter_id = "quality_parameter_"+str(i.id)
            try:
                score[parameter_id] =  QualityOfEmployee.objects.get(month=month , year = year , user =user , parameter=i).value
            except:
                score[parameter_id] = 0
    except:
        pass
    context["score"]=score
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
            context["current_quality"]= int(round(all_score /all_weight , 0))
        else:
            context["current_quality"]= 0

        all_weight = 0
        all_score=0
        for i in prev_quality:
            all_score += i.parameter.weight * i.value
            all_weight += i.parameter.weight 
        if all_weight > 0 and all_score > 0:
            context["prev_quality"]= int(round(all_score /all_weight , 0))
        else:
            context["prev_quality"]= 0            
    except:
        pass
    return  JsonResponse(context)
