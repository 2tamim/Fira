from django.contrib.auth.models import User
from ...models import Employee, DailyPerformanceReport, MonthlyPerformanceReport, TaskProgress, TaskTime, Task, QualityOfEmployee, Report ,\
    AutoEvaluationCriteria, AutoEvaluationLog, EvaluationCriteriaGroup, EvaluationCriteria, EvaluationNote, EvaluationLog, \
        EvaluationConsquenseType,Organization_Group, EvaluationCriteriaGroupWeight, SyntheticEvaluationCriteria, MonthStatistic
from ...utilities.date_tools import ConvertToSolarDate,GetWeekDay,GetPersianMonthName,ConvertToMiladi
from ...Serializers.evaluation_criteria_serializer import EvaluationCriteriaSerializer , EvaluationNoteSerializer
from django.db.models import Q, F, Value, IntegerField, Prefetch, Avg, Sum, ExpressionWrapper, Case, When
from django.db.models.functions import ExtractDay, Now, TruncDay
from django.contrib import messages
from django.shortcuts import render
import openpyxl
import xlrd
import jdatetime
import datetime
import requests
from datetime import timedelta
from datetime import time
from django.core import serializers
from rest_framework.renderers import JSONRenderer
from django.http import HttpResponseRedirect , HttpResponse, Http404, JsonResponse
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
import decimal

def convert_time(x):
    if x == '0':
        return  timedelta(hours = 0, minutes = 0)
    else:
        h = int(x.split(':')[0])
        m = int(x.split(':')[1])
        time =  timedelta(hours = h, minutes = m)
        return time

@login_required(login_url='user:login') #redirect when user is not logged in
def index(request):
    context={}
    _date_time_now = datetime.datetime.now()
    # filters
    try:
        evaluatee_id = abs(int(request.GET.get("u_id","")))
        if evaluatee_id == 0:
            evaluatee_id = request.user.id
    except:
        evaluatee_id = request.user.id

    try:
        selected_year = abs(int(request.GET.get("year","")))
    except:
        selected_year = int( ConvertToSolarDate(datetime.datetime.now()).split("/")[0] )

    try:
        selected_month = abs(int(request.GET.get("month","")))
    except:
        selected_month = int( ConvertToSolarDate(datetime.datetime.now()).split("/")[1] )
        if selected_month > 1:
            selected_month -= 1
        else:
            selected_month = 12
            selected_year -=1

    try:
        edit_value = abs(int(request.GET.get("edit","")))
    except:
        edit_value = 0

    try: 
        switch_staff = request.GET.get("staff","") == "True"
    except:
        switch_staff = False


    if request.method == "POST":
        
        context["edit_value"] = 1
        
        if "human_capitals_filters_selected_user" in request.POST:
            try:
                evaluatee_id = int(request.POST["human_capitals_filters_selected_user"])
            except:
                evaluatee_id = request.user.id
        else:
            evaluatee_id = request.user.id
        _evaluatee = User.objects.get(id=evaluatee_id)
        _evaluator = request.user

        if "human_capitals_selected_year_input" in request.POST:
            try:
                _year = int(request.POST["human_capitals_selected_year_input"])
            except:
                _year = int(ConvertToSolarDate(_date_time_now).split("/")[0])
        else:
            _year = int(ConvertToSolarDate(_date_time_now).split("/")[0])
        context["human_capitals_selected_year"] = _year

        if "human_capitals_selected_month_input" in request.POST:
            try:
                _month = int(request.POST["human_capitals_selected_month_input"])
            except:
                _month = int(ConvertToSolarDate(_date_time_now).split("/")[1])
        else:
            _month = int(ConvertToSolarDate(_date_time_now).split("/")[1])
        context["human_capitals_selected_month"] = _month


    if request.method == "GET" and request.user.id == evaluatee_id:
        _employee = Employee.objects.get(user__id = request.user.id)
        _employee.has_change_in_human_capitals = False
        _employee.save()
    # year selection options
    context["human_capitals_this_year_range"]= list(range(int(ConvertToSolarDate(_date_time_now).split("/")[0]) ,int(ConvertToSolarDate(_date_time_now).split("/")[0])-10 ,-1))
    
        

    # selections/year
    context["human_capitals_selected_user_id"] = evaluatee_id
    if selected_year in context["human_capitals_this_year_range"]:
        context["human_capitals_selected_year"] = selected_year
    else:
        context["human_capitals_selected_year"] = int(ConvertToSolarDate(_date_time_now).split("/")[0])
    # selections/month
    if selected_month < 13 and selected_month > 0:
        context["human_capitals_selected_month"] = selected_month
    else:
        context["human_capitals_selected_month"] = int(ConvertToSolarDate(_date_time_now).split("/")[1])

    if MonthStatistic.objects.filter(user_id = evaluatee_id, year = context["human_capitals_selected_year"], month = context["human_capitals_selected_month"]).exists():
        context["month_stat"] = MonthStatistic.objects.get(user_id = evaluatee_id, year = context["human_capitals_selected_year"], month = context["human_capitals_selected_month"])
    else:
        context["month_stat"] = None

    if edit_value == 1:
        context["edit_value"] = 1
    else:
        context["edit_value"] = 0
    
    #activated_menu
    request.session["activated_menu"]="human_capitals"

    # user_selection_list
    if request.user.employee.in_staff_group:
        try:
            context["user_selection_list"] = User.objects.filter(is_active=True).filter(Q(pk__in=request.user.employee.GetEmployeeTopParent.employee.GetAllChildrenUserId)|Q(pk=request.user.employee.GetEmployeeTopParent.id)).order_by('last_name')
        except:
            pass
    elif request.user.employee.GetEmployeeParent != None:
        try:
            context["user_selection_list"] = User.objects.filter(is_active=True).filter(Q(pk__in=request.user.employee.GetAllChildrenUserId)|Q(pk=request.user.employee.GetEmployeeParent)|
            Q(pk__in=User.objects.get(pk = request.user.employee.GetEmployeeParent).employee.GetDirectChildrenUserId)).order_by('last_name')
        except:
            pass
    else:
        try:
            context["user_selection_list"] = User.objects.filter(is_active=True).filter(Q(pk__in=request.user.employee.GetAllChildrenUserId)|Q(pk=request.user.employee.GetEmployeeParent)|Q(pk=request.user.id)).order_by('last_name')
        except:
            pass
    
    if EvaluationCriteria.objects.filter(evaluated_by_all = True).exists():
        group_list = EvaluationCriteria.objects.filter(evaluated_by_all = True).values_list('group__pk',flat = True)
        org_group_list = EvaluationCriteriaGroupWeight.objects.filter(criteria_group__in = group_list, weight__gt = 0).values_list('org_group__pk', flat = True)
        context["user_selection_list"] |= User.objects.filter(is_active=True).filter(employee__organization_group__in = org_group_list)

    if not context["user_selection_list"].filter(pk = evaluatee_id).exists():
        return Http404()

    # autorization levels
    context["isManager"]=False
    if(request.user.employee.organization_group.manager==request.user):
        context["isManager"] = True

    if evaluatee_id  in request.user.employee.GetDirectChildrenUserId:
        context["isDirectManager"] = True

    if(len(request.user.locumtenens_organization_groups.all())>0):
        context["isLocuntenens"] = True

    is_undiredtmanager = False 
    if(evaluatee_id  in request.user.employee.GetAllChildrenUserId and evaluatee_id not in request.user.employee.GetDirectChildrenUserId):
        context["isUnDirectManager"] = True
        is_undiredtmanager = True

    context["isTopManager"]=False
    if(request.user.employee.GetEmployeeTopParent == request.user):
        context["isTopManager"] = True

   
    # selected user manager check
    is_manager = False
    try:
        if evaluatee_id in request.user.employee.GetDirectChildrenUserId:
            is_manager = True
    except:
        is_manager = False

    # selected user sibling check
    is_sibling = False
    try:
        if evaluatee_id in User.objects.get(pk = request.user.employee.GetEmployeeParent).employee.GetDirectChildrenUserId and evaluatee_id != request.user.id:
            is_sibling = True
    except:
        is_sibling = False

    # selected user subaltern check
    is_subaltern = False
    try:
        if request.user.employee.GetEmployeeParent == evaluatee_id and request.user.employee.GetEmployeeParent != request.user.id:
            is_subaltern = True
    except:
        is_subaltern = False

    # selected user staff check
    context["switch_staff"] = False
    is_staff = False
    try:
        if request.user.employee.in_staff_group or context["isTopManager"] :
            is_staff = True
            context["switch_staff"] = switch_staff 
    except:
        is_staff = False
    context["isStaff"] = is_staff

    # selected user unrelated check
    is_unrelated = False
    if (not is_staff) and (not is_sibling) and (not is_manager) and (not is_undiredtmanager) and (not is_subaltern) and (not evaluatee_id == request.user.id):
        is_unrelated = True

    if evaluatee_id == request.user.id:
        context["edit_value"] = 0

    if (not is_staff) and (is_subaltern or is_sibling or is_unrelated) :
        context["edit_value"] = 1

    # criterias    
    criterias = EvaluationCriteria.objects.filter(evaluated_by_all = True)
    if is_sibling:
        criterias |= EvaluationCriteria.objects.filter(evaluated_by_siblings = True)
    if is_subaltern:
        criterias |= EvaluationCriteria.objects.filter(evaluated_by_subaltern = True)

    if is_staff and context["edit_value"] == 1:
        criterias |= EvaluationCriteria.objects.filter(evaluated_by_staff = True)

    if is_staff and switch_staff and context["edit_value"] == 1:
        criterias |= EvaluationCriteria.objects.all()

    if is_undiredtmanager and context["edit_value"] == 1:
        criterias |= EvaluationCriteria.objects.filter(evaluated_by_headmaster = True)

    if is_manager and context["edit_value"] == 1:
        criterias |= EvaluationCriteria.objects.filter(evaluated_by_manager = True)

    
    if context["edit_value"] == 0 and ( is_staff or is_manager or is_undiredtmanager  or evaluatee_id == request.user.id ):
        criterias |= EvaluationCriteria.objects.all()

    evaluatee_org_group = Employee.objects.get(user__id = evaluatee_id).organization_group
    groups = EvaluationCriteriaGroupWeight.objects.filter(org_group = evaluatee_org_group , weight__gt = 0).values_list('criteria_group__pk', flat = True)
    criterias = criterias.filter(group__in = groups)
    


    selected_user = User.objects.get(pk = evaluatee_id)
    if selected_user.employee.IsManager :
        criterias = criterias.filter(group__managers_special=True)
        auto_criterias = AutoEvaluationCriteria.objects.exclude(manager_criteria = None)
    else:
        criterias = criterias.filter(group__managers_special=False)
        auto_criterias = AutoEvaluationCriteria.objects.exclude(criteria = None)

    context["auto_criteria_log"] = AutoEvaluationLog.objects.filter(year = context["human_capitals_selected_year"], month = context["human_capitals_selected_month"],\
        evaluatee = selected_user, auto_criteria__in = auto_criterias)

    context["groups"] = EvaluationCriteriaGroup.objects.filter(pk__in = criterias.values_list('group__pk', flat = True)).prefetch_related(Prefetch('org_group_weights',\
          queryset=EvaluationCriteriaGroupWeight.objects.filter(org_group = evaluatee_org_group, weight__gt = 0), to_attr = "current_org_group_weights"))
    
    criterias = criterias.annotate(average_score = Value(0,IntegerField()))
    context["synthetic_evaluation_criteria"] = []
    if context["edit_value"] == 0:
        if context["switch_staff"] :        
            logs = EvaluationLog.objects.filter(evaluation_year = selected_year, evaluation_month = selected_month, evaluatee__id = evaluatee_id, staff_log = True)
            for _criteria in criterias:
                if _criteria.pk in logs.values_list('criteria__pk', flat = True):
                    sum_score = 0
                    sum_weight = 0
                    for log in logs.filter(criteria = _criteria):
                        sum_score += log.score * log.relation_weight
                        sum_weight += log.relation_weight
                    if sum_weight > 0 :
                        _criteria.average_score = sum_score / sum_weight
                    else:
                        _criteria.average_score = 50

        else:
            logs = EvaluationLog.objects.filter(evaluation_year = selected_year, evaluation_month = selected_month, evaluatee__id = evaluatee_id, staff_log = False)
            synth_eval_crits = SyntheticEvaluationCriteria.objects.all().annotate(sum_score = Value(0,IntegerField())).annotate(sum_weight = Value(0,IntegerField())).annotate(avg = Value(50,IntegerField()))
            for _criteria in criterias:
                if _criteria.pk in logs.values_list('criteria__pk', flat = True):
                    sum_score = 0
                    sum_weight = 0
                    for log in logs.filter(criteria = _criteria):
                        sum_score += log.score * log.relation_weight
                        sum_weight += log.relation_weight
                    if sum_weight > 0 :
                        _criteria.average_score = sum_score / sum_weight
                    else:
                        _criteria.average_score = 50

                    for synth_crit in synth_eval_crits:
                        if _criteria in synth_crit.criterias.all():
                            synth_crit.sum_score += _criteria.average_score * _criteria.weight
                            synth_crit.sum_weight += _criteria.weight
                            if synth_crit.sum_weight > 0:
                                synth_crit.avg = int(synth_crit.sum_score / synth_crit.sum_weight)

            context["synthetic_evaluation_criteria"] = synth_eval_crits
            

    else:
        if context["switch_staff"] : 
            logs = EvaluationLog.objects.filter(evaluation_year = selected_year, evaluation_month = selected_month, evaluatee__id = evaluatee_id, evaluator = request.user, staff_log = True)
            for _criteria in criterias:
                if _criteria.pk in logs.values_list('criteria__pk', flat = True):
                    _criteria.average_score =  logs.get(criteria = _criteria).score
        else:
            logs = EvaluationLog.objects.filter(evaluation_year = selected_year, evaluation_month = selected_month, evaluatee__id = evaluatee_id, evaluator = request.user, staff_log = False)
            for _criteria in criterias:
                if _criteria.pk in logs.values_list('criteria__pk', flat = True):
                    _criteria.average_score =  logs.get(criteria = _criteria).score
        
    context["evaluation_log"] = logs
    context["criterias"] = criterias


    
    evaluatee_notes = []
    if context["edit_value"] == 0: 
        criterias_list = criterias.values_list('pk', flat=True )

        if evaluatee_id == request.user.id or evaluatee_id in request.user.employee.GetAllChildrenUserId:
            evaulation_criteria_notes = EvaluationNote.objects.filter( evaluatee__id = evaluatee_id, criteria__id__in = criterias_list, year = selected_year ,month = selected_month, private = False )
        else:
            evaulation_criteria_notes = EvaluationNote.objects.filter( evaluatee__id = evaluatee_id, criteria__id__in = criterias_list, year = selected_year ,month = selected_month ,show_to_all = True, private = False )
        evaulation_criteria_notes |= EvaluationNote.objects.filter( evaluatee__id = evaluatee_id, criteria__id__in = criterias_list, year = selected_year ,month = selected_month,show_to_all = True, private = True )
        evaulation_criteria_notes |= EvaluationNote.objects.filter( evaluatee__id = evaluatee_id, evaluator__id = request.user.id, criteria__id__in = criterias_list, year = selected_year ,month = selected_month )

        if context["switch_staff"] :
            evaulation_criteria_notes = evaulation_criteria_notes.filter(staff_note = True)
        else:
            evaulation_criteria_notes = evaulation_criteria_notes.filter(staff_note = False)

        for note in evaulation_criteria_notes.order_by('criteria__id'):
            evaluatee_notes.append(note)
        context["notes"] = evaluatee_notes
    else:
        context["notes"] = []

    public_notes = []
    public_notes = EvaluationNote.objects.filter(evaluatee__id = evaluatee_id, year = selected_year ,month = selected_month, show_to_all = True).exclude(consequence_amount = 0 )
    if len(public_notes) > 0:
        context["public_reward_punishment"] = public_notes
    else:
        context["public_reward_punishment"] = None 

    context["evaluation_consequense_type"] = EvaluationConsquenseType.objects.all()


    if request.method == "POST":
        try:
            

            for criteria in criterias:
                criteria_score_id = "human_capitals_criteria_id_input_"+str(criteria.id)
                if criteria_score_id in request.POST: 
                    try:
                        _score = int(request.POST[criteria_score_id])
                        if _score <10 or _score> 100:
                            _score = 50  # default value without error
                    except:
                        _score = None #default value 
                    if _score != None :
                        try:
                            evaluation_log = EvaluationLog.objects.get(evaluation_year = _year, evaluation_month = _month, \
                                evaluatee = _evaluatee, evaluator =_evaluator, criteria = criteria, staff_log = switch_staff )
                            max_weight = 0
                            if is_manager and criteria.evaluation_by_manager_weight:
                                evaluation_log.evaluation_relation = 0
                                max_weight = criteria.evaluation_by_manager_weight
                            if is_sibling and criteria.evaluation_by_siblings_weight and criteria.evaluation_by_siblings_weight > max_weight:
                                evaluation_log.evaluation_relation = 1
                                max_weight = criteria.evaluation_by_siblings_weight
                            if is_subaltern and criteria.evaluation_by_subaltern_weight and criteria.evaluation_by_subaltern_weight > max_weight:
                                evaluation_log.evaluation_relation = 2
                                max_weight = criteria.evaluation_by_subaltern_weight
                            if is_staff and criteria.evaluation_by_staff_weight and criteria.evaluation_by_staff_weight > max_weight:
                                evaluation_log.evaluation_relation = 3
                                max_weight = criteria.evaluation_by_staff_weight
                            if is_undiredtmanager and criteria.evaluation_by_headmaster_weight and criteria.evaluation_by_headmaster_weight > max_weight:
                                evaluation_log.evaluation_relation = 4
                                max_weight = criteria.evaluation_by_headmaster_weight
                            if criteria.evaluation_by_all_weight and criteria.evaluation_by_all_weight > max_weight:
                                evaluation_log.evaluation_relation = 5
                                max_weight = criteria.evaluation_by_all_weight

                            if context["switch_staff"]:
                                evaluation_log.evaluation_relation = 3
                                max_weight = 1
                                evaluation_log.staff_log = True
                            else:
                                evaluation_log.evaluatee.employee.has_change_in_human_capitals = True
                                evaluation_log.evaluatee.employee.save()
                            
                            evaluation_log.relation_weight = max_weight
                            evaluation_log.score= _score
                            evaluation_log.save() 
                        except:
                            evaluation_log = EvaluationLog()
                            evaluation_log.evaluation_year = _year
                            evaluation_log.evaluation_month = _month
                            evaluation_log.evaluatee = _evaluatee
                            evaluation_log.evaluator =_evaluator
                            evaluation_log.criteria = criteria
                            evaluation_log.score= _score
                            max_weight = 0
                            if is_manager and criteria.evaluation_by_manager_weight:
                                evaluation_log.evaluation_relation = 0
                                max_weight = criteria.evaluation_by_manager_weight
                            if is_sibling and criteria.evaluation_by_siblings_weight and criteria.evaluation_by_siblings_weight > max_weight:
                                evaluation_log.evaluation_relation = 1
                                max_weight = criteria.evaluation_by_siblings_weight
                            if is_subaltern and criteria.evaluation_by_subaltern_weight and criteria.evaluation_by_subaltern_weight > max_weight:
                                evaluation_log.evaluation_relation = 2
                                max_weight = criteria.evaluation_by_subaltern_weight
                            if is_staff and criteria.evaluation_by_staff_weight and criteria.evaluation_by_staff_weight > max_weight:
                                evaluation_log.evaluation_relation = 3
                                max_weight = criteria.evaluation_by_staff_weight
                            if is_undiredtmanager and criteria.evaluation_by_headmaster_weight and criteria.evaluation_by_headmaster_weight > max_weight:
                                evaluation_log.evaluation_relation = 4
                                max_weight = criteria.evaluation_by_headmaster_weight
                            if criteria.evaluation_by_all_weight and criteria.evaluation_by_all_weight > max_weight:
                                evaluation_log.evaluation_relation = 5
                                max_weight = criteria.evaluation_by_all_weight

                            if context["switch_staff"]:
                                evaluation_log.evaluation_relation = 3
                                max_weight = 1
                                evaluation_log.staff_log = True
                            else:
                                evaluation_log.evaluatee.employee.has_change_in_human_capitals = True
                                evaluation_log.evaluatee.employee.save()
                            
                            evaluation_log.relation_weight = max_weight
                            
                            evaluation_log.save()
            messages.success(request, 'ثبت شد')  



            criterias = criterias.annotate(average_score = Value(0,IntegerField()))

            if context["switch_staff"]:
                logs = EvaluationLog.objects.filter(evaluation_year = selected_year, evaluation_month = selected_month, evaluatee__id = evaluatee_id, evaluator = request.user, staff_log = True)
                for _criteria in criterias:
                    if _criteria.pk in logs.values_list('criteria__pk', flat = True):
                        _criteria.average_score =  logs.get(criteria = _criteria).score
            else :
                logs = EvaluationLog.objects.filter(evaluation_year = selected_year, evaluation_month = selected_month, evaluatee__id = evaluatee_id, evaluator = request.user, staff_log = False)
                for _criteria in criterias:
                    if _criteria.pk in logs.values_list('criteria__pk', flat = True):
                        _criteria.average_score =  logs.get(criteria = _criteria).score
            
            context["evaluation_log"] = logs
            context["criterias"] = criterias

        except:
            pass    

    return render(request, 'human_capitals/list.html', {'context':context})

@login_required(login_url='user:login') #redirect when user is not logged in
def criteria_description(request):

    try: 
        switch_staff = request.GET.get("staff","") == "True"
    except:
        switch_staff = False

    try:
        evaluatee_id = int(request.POST["human_capitals_criteria_description_user"])
    except:
        data['message']=err.args[0]
        return JsonResponse(data)

    evaluator = request.user
    try:
        criteria_id = request.POST["human_capitals_criteria_description_criteria"]
        criteria = EvaluationCriteria.objects.get(id = criteria_id)
    except:
        data['message']="شاخص نامعتبر"
        return JsonResponse(data)

    _note = None
    if request.POST["human_capitals_criteria_description_note"] :
        try:
            note_id = int(request.POST["human_capitals_criteria_description_note"])
            _note = EvaluationNote.objects.get(pk = note_id)
            if _note.evaluator != request.user:
                return PermissionDenied
        except:
            data['message']="شناسه نظر غیر معتبر است"
            return JsonResponse(data)

    try:
        # selected user self check
        if evaluator.id == evaluatee_id:
            return PermissionDenied
        # selected user manager check
        elif evaluatee_id in request.user.employee.GetAllChildrenUserId and( criteria.evaluated_by_manager or criteria.evaluated_by_headmaster):
            pass
        # selected user sibling check
        elif evaluatee_id in User.objects.get(pk = request.user.employee.GetEmployeeParent).employee.GetDirectChildrenUserId and evaluatee_id != request.user.id and criteria.evaluated_by_siblings:
            pass
        # selected user subaltern check
        elif request.user.employee.GetEmployeeParent == evaluatee_id and criteria.evaluated_by_subaltern:
            pass
        # selected user staff check
        elif request.user.employee.in_staff_group and (criteria.evaluated_by_staff or switch_staff):
            pass
        elif criteria.evaluated_by_all:
            pass
        else:
            return PermissionDenied
    except:
        return PermissionDenied

    data={}
    
    try:
        if _note:
            note = _note
        else:
            note = EvaluationNote()
            note.evaluatee = User.objects.get(id = evaluatee_id)
            note.year = int(request.POST["human_capitals_criteria_description_year"])
            note.month = int(request.POST["human_capitals_criteria_description_month"])
            note.evaluator = request.user
            if "human_capitals_criteria_description_criteria" in request.POST:
                criteria_id = request.POST["human_capitals_criteria_description_criteria"]
                note.criteria = EvaluationCriteria.objects.get(id = criteria_id)
        if "human_capitals_criteria_description_text" in request.POST:
            note.note = request.POST["human_capitals_criteria_description_text"]
        if "human_capitals_criteria_descriptions_show_to_all" in request.POST:
            to_all = int(request.POST["human_capitals_criteria_descriptions_show_to_all"])
            if to_all == 1:
                note.show_to_all = True
                note.privacy = False
            elif to_all == 0:
                note.show_to_all = False
                note.private = False
            elif to_all == 2:
                note.show_to_all = False
                note.private = True
            else:
                note.show_to_all = True
                note.private = True
            
            

        if 'human_capitals_criteria_description_cons_type' in request.POST and int(request.POST["human_capitals_criteria_description_cons_type"]) > 0 :
            try :
                if evaluatee_id in request.user.employee.GetAllChildrenUserId:
                    note.consequence_type = EvaluationConsquenseType.objects.get(pk=int(request.POST["human_capitals_criteria_description_cons_type"]))
                    try:
                        note.consequence_amount = int(request.POST["human_capitals_criteria_description_amount"])
                    except:
                        note.consequence_amount = 0             
            except :
                pass
        note.staff_note = switch_staff
        note.save()
        data["messege"] = "ذخیره نظر با موفقیت انجام شد"
        return  JsonResponse(data)
    except:
        data['message']=err.args[0]
        return JsonResponse(data)

@login_required(login_url='user:login') #redirect when user is not logged in
def get_notes(request):
    evaluatee_id = int(request.GET.get("u_id",""))
    evaluator = request.user

    try:
        # selected user self check
        if evaluator.id == evaluatee_id:
            pass
        # selected user manager check
        elif evaluatee_id in request.user.employee.GetAllChildrenUserId:
            pass
        # selected user sibling check
        elif evaluatee_id in User.objects.get(pk = request.user.employee.GetEmployeeParent).employee.GetDirectChildrenUserId and evaluatee_id != request.user.id:
            pass
        # selected user subaltern check
        elif request.user.employee.GetEmployeeParent == evaluatee_id:
            pass
        # selected user staff check
        elif request.user.employee.in_staff_group:
            pass
        else:
            return PermissionDenied
    except:
        return PermissionDenied

    data={}
    try:
        criteria_id = int(request.GET.get("c_id",""))
        _user = request.user
        year = int(request.GET.get("year",""))
        month = int(request.GET.get("month",""))

        try:
            evaulation_criteria_notes = EvaluationNote.objects.filter(evaluator = _user , evaluatee__id = evaluatee_id, criteria__id = criteria_id, year = year ,month = month )
            evaulation_criteria_notes |= EvaluationNote.objects.filter( evaluatee__id = evaluatee_id, criteria__id = criteria_id, year = year ,month = month, show_to_all = True, private = False )
            if evaluatee_id in request.user.employee.GetAllChildrenUserId :
                evaulation_criteria_notes |= EvaluationNote.objects.filter( evaluatee__id = evaluatee_id, criteria__id = criteria_id, year = year ,month = month, private = False )
            if evaluatee_id == request.user.id :
                evaulation_criteria_notes |= EvaluationNote.objects.filter( evaluatee__id = evaluatee_id, criteria__id = criteria_id, year = year ,month = month).exclude(private = True, show_to_all=False)
            notes = EvaluationNoteSerializer(evaulation_criteria_notes, many=True)
            data["notes"]=JSONRenderer().render(notes.data).decode("utf-8") 
        except:
            data["notes"] = []
        return JsonResponse(data)
            
        #raise PermissionDenied
    except Exception as err:
        data['message']=err.args[0]
    return JsonResponse(data)


@login_required(login_url='user:login') #redirect when user is not logged in
def delete_note(request , note_id):

    
    evaluator = request.user
 
    try:
        _note=EvaluationNote.objects.get(pk=int(note_id))
        if _note.evaluator == request.user :
            _note.delete()
            return  HttpResponse(True)
        else:
            raise PermissionDenied
    except Exception as err:
        return  HttpResponse(False)
            
    return  HttpResponse(False)



@login_required(login_url='user:login') #redirect when user is not logged in
def upload_excel(request):
    if(request.user.employee.organization_group.manager != request.user or request.user.employee.GetEmployeeParent != None) and (not request.user.employee.in_staff_group):
        raise PermissionDenied
    
    else:
        excel_file = request.FILES["human_capitals_file_upload"]

        if not excel_file.name.endswith('.xls'):
            messages.warning(request, 'نوع فایل ارسالی معتبر نیست')
            return HttpResponseRedirect(request.GET['next'])

        try:
            file = xlrd.open_workbook(file_contents=excel_file.read())
        except:
            messages.warning(request, 'محتوی فایل قابل خواندن نیست')
            return HttpResponseRedirect(request.GET['next'])

        for sh in file.sheets():
            sh_name = sh.name
            sh_rows = sh.nrows
            sh_cols = sh.ncols

            excel_data = list()
            personelnumber = str(int(sh.cell_value(rowx=3, colx=27)))
            solar_date = str(sh.cell_value(rowx=5, colx=2))
            solar_year = int(solar_date.split('/')[0])
            solar_month = int(solar_date.split('/')[1])
            delay_count = 0



            try:
                report_employee = Employee.objects.get(personelnumber=personelnumber)
                for rx in range(7,sh_rows - 5 ):
                    solar_d = solar_date.split('/')[0]+'/'+ sh.cell_value(rowx=rx, colx=30)
                    if not DailyPerformanceReport.objects.filter(solar_date = solar_d , user = report_employee.user ).exists():
                        daily_report = DailyPerformanceReport()
                    else: 
                        daily_report = DailyPerformanceReport.objects.get(solar_date = solar_d , user = report_employee.user)
                    daily_report.user = report_employee.user

                    daily_report.solar_date = solar_d

                    gregorian_date = jdatetime.date(int(solar_date.split('/')[0]),int(sh.cell_value(rowx=rx, colx=30).split('/')[0]),int(sh.cell_value(rowx = rx, colx=30).split('/')[1])).togregorian()
                    daily_report.g_date = gregorian_date
                    
                    x = sh.cell_value(rowx = rx, colx=26)
                    if not x:
                        daily_report.entry1 = None
                    else:
                        daily_report.entry1 =datetime.datetime(gregorian_date.year, gregorian_date.month, gregorian_date.day, int(x.split(':')[0]), int(x.split(':')[1]))

                    if sh.cell_value(rowx= rx, colx=8) != '':
                        delay_count += 1

                    status = sh.cell_value(rowx= rx, colx=1)    
                    daily_report.status = status
                    daily_report.save()    

                if not MonthlyPerformanceReport.objects.filter(solar_year = solar_year, solar_month = solar_month , user = report_employee.user).exists():
                    monthly_report = MonthlyPerformanceReport()
                else:
                    monthly_report = MonthlyPerformanceReport.objects.get(solar_year = solar_year, solar_month = solar_month , user = report_employee.user)
                
                monthly_report.user = report_employee.user

                monthly_report.solar_year = int(solar_date.split('/')[0])

                monthly_report.solar_month = solar_month

                monthly_report.month_days = int(sh.cell_value(rowx=sh_rows - 1, colx=29))

                monthly_report.month_holidays = int(sh.cell_value(rowx=sh_rows - 1, colx=14))

                a1 = sh.cell_value(rowx=sh_rows-5, colx=3)
                try:
                    if a1:
                        pass
                    else:
                        a1 = '00:00'
                    monthly_report.holiday_overtime_duration = convert_time(a1) 
                except:
                    monthly_report.holiday_overtime_duration = convert_time('00:00')

                a2 = sh.cell_value(rowx=sh_rows-5, colx=4)
                try:
                    if a2:
                        pass
                    else:
                        a2 = '00:00'
                    monthly_report.overtime_duration = convert_time(a2)
                except:
                    monthly_report.overtime_duration = convert_time('00:00') 

                a3 = sh.cell_value(rowx=sh_rows-5, colx=6)
                try:
                    if a3:
                        pass
                    else:
                        a3 = '00:00'
                    monthly_report.lowtime_duration = convert_time(a3)
                except:
                    monthly_report.lowtime_duration = convert_time('00:00')

                a4 = sh.cell_value(rowx=sh_rows-5, colx=7)
                try:
                    if a4:
                        pass
                    else:
                        a4 = '00:00'
                    monthly_report.rush_hours_duration = convert_time(a4)
                except:
                    monthly_report.rush_hours_duration = convert_time('00:00') 

                a5 = sh.cell_value(rowx=sh_rows-5, colx=8)
                try:
                    if a5:
                        pass
                    else:
                        a5 = '00:00'
                    monthly_report.delay_hours_duration = convert_time(a5)
                except:
                    monthly_report.delay_hours_duration = convert_time('00:00') 

                a6 = sh.cell_value(rowx=sh_rows-5, colx=9)
                try:
                    if a6:
                        pass
                    else:
                        a6 = '00:00'
                    monthly_report.leave_hours_duration = convert_time(a6) 
                except:
                    monthly_report.leave_hours_duration = convert_time('00:00')

                a7 = sh.cell_value(rowx=sh_rows-5, colx=13)
                try:
                    if a7:
                        pass
                    else:
                        a7 = '00:00'
                    monthly_report.performance_duration = convert_time(a7) 
                except:
                    monthly_report.performance_duration = convert_time('00:00')

                a8 = sh.cell_value(rowx=sh_rows-5, colx=15)
                try:
                    if a8:
                        pass
                    else:
                        a8 = '00:00'
                    monthly_report.presence_duration = convert_time(a8) 
                except:
                    monthly_report.presence_duration = convert_time('00:00')

                a9 = sh.cell_value(rowx=sh_rows-5, colx=26)
                try:
                    if a9:
                        pass
                    else:
                        a9 = '00:00'
                    monthly_report.entry_sum_duration = convert_time(a9)
                except:
                    monthly_report.entry_sum_duration = convert_time('00:00')

                monthly_report.delay_count = delay_count
                monthly_report.save()

                #######################################################  Calculate Auto Criterias   ##############################################
                month_start = jdatetime.datetime(year = solar_year, month = solar_month, day = 1).togregorian()
                if solar_month == 12:
                    month_end = jdatetime.datetime(year = solar_year + 1, month = 1, day = 1).togregorian()
                else:
                    month_end = jdatetime.datetime(year = solar_year , month = solar_month + 1, day = 1).togregorian()

                month_tasks = Task.objects.filter(Q(user_assignee = report_employee.user)|Q(group_assignee__head = report_employee.user), cancelled = False,\
                    enddate__gte = month_start.date(), enddate__lt = month_end.date())

                month_task_times = TaskTime.objects.filter(user = report_employee.user, start__gte = month_start, end__lt = month_end)

                month_reports = Report.objects.filter(task_time__pk__in = month_task_times.values_list('pk', flat = True))

                subaltern_month_task_times = TaskTime.objects.filter(user__pk__in = report_employee.GetDirectChildrenUserId, start__gte = month_start, end__lt = month_end)

                subaltern_month_reports = Report.objects.filter(task_time__pk__in = subaltern_month_task_times.values_list('pk', flat = True), confirmed = True)

                if AutoEvaluationCriteria.objects.filter(slug = 'taskscore').exists():
                    try:
                        current_log = AutoEvaluationLog.objects.get(evaluatee = report_employee.user, year = solar_year, month = solar_month,\
                            auto_criteria__slug = 'taskscore' )
                    except:
                        current_log = AutoEvaluationLog()
                        current_log.evaluatee = report_employee.user
                        current_log.year = solar_year
                        current_log.month = solar_month
                        current_log.auto_criteria = AutoEvaluationCriteria.objects.get(slug = 'taskscore')
                    
                    
                    
                    month_root_tasks = month_tasks.exclude(score = None).exclude(task_parent__pk__in = month_tasks.values_list('pk', flat = True)).aggregate(Avg('score'))
                    if month_root_tasks['score__avg'] :
                        current_log.int_value = int(month_root_tasks['score__avg'] * 10)
                    else:
                        current_log.int_value = 50
                    
                    current_log.save()
                       
                
                if AutoEvaluationCriteria.objects.filter(slug = 'taskdelay').exists():
                    try:
                        current_log = AutoEvaluationLog.objects.get(evaluatee = report_employee.user, year = solar_year, month = solar_month,\
                            auto_criteria__slug = 'taskdelay' )
                    except:
                        current_log = AutoEvaluationLog()
                        current_log.evaluatee = report_employee.user
                        current_log.year = solar_year
                        current_log.month = solar_month
                        current_log.auto_criteria = AutoEvaluationCriteria.objects.get(slug = 'taskdelay')
                    
                    month_tasks_delay = month_tasks

                    
                    
                    month_tasks_delay = month_tasks_delay.annotate(delay_percent = Case(
                            When(progress_complete_date= None, then= ExpressionWrapper((ExtractDay(Now()-F('startdate')) + Value(1)) * Value(100) / (ExtractDay(F('enddate')-F('startdate')) + Value(1)), IntegerField())),
                            default = ExpressionWrapper((ExtractDay(F('progress_complete_date')-F('startdate')) + Value(1)) * Value(100) / (ExtractDay(F('enddate')-F('startdate')) + Value(1)), IntegerField()),
                        ))
                     
                    
                    month_tasks_delay = month_tasks_delay.aggregate(Avg('delay_percent'))
                    if month_tasks_delay['delay_percent__avg'] :
                        task_delay_index = int(month_tasks_delay['delay_percent__avg'])
                        if task_delay_index > 100:
                            if task_delay_index > 162 :
                                current_log.int_value = 0
                            else:
                                current_log.int_value = int((162-task_delay_index)*1.6)
                        else:
                            current_log.int_value = 100
                    else:
                        current_log.int_value = 50
                    
                    current_log.save()


                if AutoEvaluationCriteria.objects.filter(slug = 'leavetime').exists():
                    try:
                        current_log = AutoEvaluationLog.objects.get(evaluatee = report_employee.user, year = solar_year, month = solar_month,\
                            auto_criteria__slug = 'leavetime' )
                    except:
                        current_log = AutoEvaluationLog()
                        current_log.evaluatee = report_employee.user
                        current_log.year = solar_year
                        current_log.month = solar_month
                        current_log.auto_criteria = AutoEvaluationCriteria.objects.get(slug = 'leavetime')
                    
                    
                    current_log.time_value_duration = monthly_report.leave_hours_duration + monthly_report.lowtime_duration
                    
                    current_log.save()


                if AutoEvaluationCriteria.objects.filter(slug = 'delaycount').exists():
                    try:
                        current_log = AutoEvaluationLog.objects.get(evaluatee = report_employee.user, year = solar_year, month = solar_month,\
                            auto_criteria__slug = 'delaycount' )
                    except:
                        current_log = AutoEvaluationLog()
                        current_log.evaluatee = report_employee.user
                        current_log.year = solar_year
                        current_log.month = solar_month
                        current_log.auto_criteria = AutoEvaluationCriteria.objects.get(slug = 'delaycount')
                    
                    
                    current_log.int_value = monthly_report.delay_count
                    
                    current_log.save()


                if AutoEvaluationCriteria.objects.filter(slug = 'delayavg').exists():
                    try:
                        current_log = AutoEvaluationLog.objects.get(evaluatee = report_employee.user, year = solar_year, month = solar_month,\
                            auto_criteria__slug = 'delayavg' )
                    except:
                        current_log = AutoEvaluationLog()
                        current_log.evaluatee = report_employee.user
                        current_log.year = solar_year
                        current_log.month = solar_month
                        current_log.auto_criteria = AutoEvaluationCriteria.objects.get(slug = 'delayavg')
                    
                    if monthly_report.delay_count > 0 :
                        current_log.time_value_duration = monthly_report.delay_hours_duration / monthly_report.delay_count
                    else:
                        current_log.time_value_duration = monthly_report.delay_hours_duration
                    
                    current_log.save()

                
                if AutoEvaluationCriteria.objects.filter(slug = 'overtime').exists():
                    try:
                        current_log = AutoEvaluationLog.objects.get(evaluatee = report_employee.user, year = solar_year, month = solar_month,\
                            auto_criteria__slug = 'overtime' )
                    except:
                        current_log = AutoEvaluationLog()
                        current_log.evaluatee = report_employee.user
                        current_log.year = solar_year
                        current_log.month = solar_month
                        current_log.auto_criteria = AutoEvaluationCriteria.objects.get(slug = 'overtime')
                    
                    
                    current_log.time_value_duration = monthly_report.overtime_duration
                    
                    current_log.save()


                if AutoEvaluationCriteria.objects.filter(slug = 'treescore').exists():
                    try:
                        current_log = AutoEvaluationLog.objects.get(evaluatee = report_employee.user, year = solar_year, month = solar_month,\
                            auto_criteria__slug = 'treescore' )
                    except:
                        current_log = AutoEvaluationLog()
                        current_log.evaluatee = report_employee.user
                        current_log.year = solar_year
                        current_log.month = solar_month
                        current_log.auto_criteria = AutoEvaluationCriteria.objects.get(slug = 'treescore')

                    try:
                        month_start_str = jdatetime.datetime.fromgregorian(date= month_start).strftime(format="%Y-%m-%d")
                        month_end_str = (jdatetime.datetime.fromgregorian(date= month_end) - jdatetime.timedelta(days = 1)).strftime(format="%Y-%m-%d")
                        url = 'http://tree.medad-art.ir/wp-json/rateme/v1/user/'+ report_employee.user.username +'/'+ month_start_str +'/' + month_end_str + '/jalali/'
                        json_resp = requests.request('GET',url).json()

                        current_log.int_value = json_resp['points']['total_points']
                    except:
                        current_log.int_value = 0
                    
                    current_log.save()

                
                if AutoEvaluationCriteria.objects.filter(slug = 'reportscore').exists():
                    try:
                        current_log = AutoEvaluationLog.objects.get(evaluatee = report_employee.user, year = solar_year, month = solar_month,\
                            auto_criteria__slug = 'reportscore' )
                    except:
                        current_log = AutoEvaluationLog()
                        current_log.evaluatee = report_employee.user
                        current_log.year = solar_year
                        current_log.month = solar_month
                        current_log.auto_criteria = AutoEvaluationCriteria.objects.get(slug = 'reportscore')
                    
                    
                    
                    month_scored_reports = month_reports.exclude(score = None).aggregate(Avg('score'))
                    if month_scored_reports['score__avg'] :
                        current_log.int_value = int(month_scored_reports['score__avg'] * 10)
                    else:
                        current_log.int_value = 50
                    
                    current_log.save()


                if AutoEvaluationCriteria.objects.filter(slug = 'reportdelay').exists():
                    try:
                        current_log = AutoEvaluationLog.objects.get(evaluatee = report_employee.user, year = solar_year, month = solar_month,\
                            auto_criteria__slug = 'reportdelay' )
                    except:
                        current_log = AutoEvaluationLog()
                        current_log.evaluatee = report_employee.user
                        current_log.year = solar_year
                        current_log.month = solar_month
                        current_log.auto_criteria = AutoEvaluationCriteria.objects.get(slug = 'reportdelay')
                    
                                        
                    month_reports = month_reports.annotate(delay_percent = Case(
                            When(created__lte = F('task_time__end') + Value( datetime.timedelta(seconds = 3600)), then = Value(100) ),
                            When(created__lte = TruncDay(F('task_time__end')) + Value( datetime.timedelta(days= 1)), then = Value(75) ),
                            When(created__lte = TruncDay(F('task_time__end')) + Value( datetime.timedelta(days= 1.5)), then = Value(50) ),
                            When(created__lte = TruncDay(F('task_time__end')) + Value( datetime.timedelta(days= 2)), then = Value(25) ),
                            default = Value(10),
                            output_field = IntegerField(),
                        ))
                     
                    
                    month_reports = month_reports.aggregate(Avg('delay_percent'))
                    if month_reports['delay_percent__avg'] :
                        current_log.int_value = int(month_reports['delay_percent__avg'])
                    else:
                        current_log.int_value = 50
                    
                    current_log.save()


                if AutoEvaluationCriteria.objects.filter(slug = 'reportacceptdelay').exists():
                    try:
                        current_log = AutoEvaluationLog.objects.get(evaluatee = report_employee.user, year = solar_year, month = solar_month,\
                            auto_criteria__slug = 'reportacceptdelay' )
                    except:
                        current_log = AutoEvaluationLog()
                        current_log.evaluatee = report_employee.user
                        current_log.year = solar_year
                        current_log.month = solar_month
                        current_log.auto_criteria = AutoEvaluationCriteria.objects.get(slug = 'reportacceptdelay')
                    
                                        
                    subaltern_month_reports = subaltern_month_reports.annotate(delay_percent = Case(
                            When(updated__lte = TruncDay(F('created')) + Value( datetime.timedelta(days= 1)), then = Value(100) ),
                            When(updated__lte = F('created') + Value( datetime.timedelta(days = 1)), then = Value(75) ),
                            When(updated__lte = F('created') + Value( datetime.timedelta(days = 2)), then = Value(50) ),
                            When(updated__lte = F('created') + Value( datetime.timedelta(days = 3)), then = Value(25) ),
                            When(updated__lte = F('created') + Value( datetime.timedelta(days = 7)), then = Value(10) ),
                            default = Value(0),
                            output_field = IntegerField(),
                        ))
                     
                    
                    subaltern_month_reports = subaltern_month_reports.aggregate(Avg('delay_percent'))
                    if subaltern_month_reports['delay_percent__avg'] :
                        current_log.int_value = int(subaltern_month_reports['delay_percent__avg'])
                    else:
                        current_log.int_value = 50
                    
                    current_log.save()


                if AutoEvaluationCriteria.objects.filter(slug = 'performance').exists():
                    try:
                        current_log = AutoEvaluationLog.objects.get(evaluatee = report_employee.user, year = solar_year, month = solar_month,\
                            auto_criteria__slug = 'performance' )
                    except:
                        current_log = AutoEvaluationLog()
                        current_log.evaluatee = report_employee.user
                        current_log.year = solar_year
                        current_log.month = solar_month
                        current_log.auto_criteria = AutoEvaluationCriteria.objects.get(slug = 'performance')
                    
                                        
                    month_task_times = month_task_times.annotate(duration = F('end')-F('start'))
                     
                    
                    sum_task_times = month_task_times.aggregate(Sum('duration'))['duration__sum']

                    try:
                        current_log.int_value = int((sum_task_times / monthly_report.presence_duration)*100)
                    except:
                        current_log.int_value = 50
                    
                    current_log.save()

            except:
                try:
                    messages.warning(request, 'پردازش اطلاعات '+ str(sh.cell_value(rowx=5, colx=27)) +' فایل با خطا مواجه شد')
                except:
                    messages.warning(request, 'پردازش اطلاعات '+ personelnumber +' فایل با خطا مواجه شد')

    return HttpResponseRedirect(request.GET['next'])


@login_required(login_url='user:login') #redirect when user is not logged in
def ShowStaffReport(request):
    if(request.user.employee.organization_group.manager != request.user or request.user.employee.GetEmployeeParent != None) and (not request.user.employee.in_staff_group):
        raise PermissionDenied

    context = {}
    _date_time_now = datetime.datetime.now()
    try:
        selected_year = abs(int(request.GET.get("year","")))
    except:
        selected_year = int( ConvertToSolarDate(datetime.datetime.now()).split("/")[0] )

    try:
        selected_month = abs(int(request.GET.get("month","")))
    except:
        selected_month = int( ConvertToSolarDate(datetime.datetime.now()).split("/")[1] )
        if selected_month > 1:
            selected_month -= 1
        else:
            selected_month = 12
            selected_year -=1

    # year selection options
    context["human_capitals_this_year_range"]= list(range(int(ConvertToSolarDate(_date_time_now).split("/")[0]) ,int(ConvertToSolarDate(_date_time_now).split("/")[0])-10 ,-1))
    
        

    # selections/year
    if selected_year in context["human_capitals_this_year_range"]:
        context["human_capitals_selected_year"] = selected_year
    else:
        context["human_capitals_selected_year"] = int(ConvertToSolarDate(_date_time_now).split("/")[0])
    # selections/month
    if selected_month < 13 and selected_month > 0:
        context["human_capitals_selected_month"] = selected_month
    else:
        context["human_capitals_selected_month"] = int(ConvertToSolarDate(_date_time_now).split("/")[1])

    try:
        order = request.GET.get("order","")
        if order == 'group' or order =='score' or order == 'staff_score' or order == 'group_staff':
            pass
        else:
            order == 'group'
    except:
        order == 'group'

    context["order"] = order

    context["isTopManager"]=False
    if(request.user.employee.GetEmployeeTopParent == request.user):
        context["isTopManager"] = True

    is_staff = False
    try:
        if request.user.employee.in_staff_group :
            is_staff = True
    except:
        is_staff = False
    context["isStaff"] = is_staff

    employees = User.objects.filter(is_active =  True, employee__organization_group__id__gt = 0)\
        .annotate(average_score = Value(0,IntegerField())).annotate(average_staff_score = Value(0,IntegerField()))
       
    for employee in employees:
        
        criterias = EvaluationCriteria.objects.filter(group__managers_special=employee.employee.IsManager)\
            .annotate(average_score = Value(50,IntegerField()))
        group_weights = EvaluationCriteriaGroupWeight.objects.filter(org_group = employee.employee.organization_group,\
             weight__gt = 0, criteria_group__managers_special=employee.employee.IsManager)
        criteria_groups = group_weights.values_list('criteria_group__pk',flat = True)
        logs = EvaluationLog.objects.filter(evaluation_year = selected_year, evaluation_month = selected_month,\
            evaluatee__id = employee.id, staff_log = False)

        total_score = 0
        total_weight = 0

        for group in EvaluationCriteriaGroup.objects.filter(pk__in = criteria_groups).prefetch_related(Prefetch('org_group_weights',\
            queryset=EvaluationCriteriaGroupWeight.objects.filter(org_group = employee.employee.organization_group, weight__gt = 0), to_attr = "weight")):
            total_score_group = 0
            total_weight_group = 0
            for criteria in criterias.filter(group = group):
                if criteria.pk in logs.values_list('criteria__pk', flat = True):
                    sum_score = 0
                    sum_weight = 0
                    for log in logs.filter(criteria = criteria):
                        sum_score += log.score * log.relation_weight
                        sum_weight += log.relation_weight
                    if sum_weight > 0 :
                        criteria.average_score = sum_score / sum_weight
                    else:
                        criteria.average_score = 50
                total_score_group += criteria.average_score * criteria.weight
                total_weight_group += criteria.weight
            if total_weight_group > 0:
                total_score += ( total_score_group / total_weight_group )* group.weight[0].weight
                total_weight +=  group.weight[0].weight
            else:
                total_score += ( 50 )* group.weight[0].weight
                total_weight +=  group.weight[0].weight

        if total_weight > 0:
            employee.average_score = round(total_score/ total_weight)
        else:
            employee.average_score = 50
        
        criterias = EvaluationCriteria.objects.filter(group__managers_special=employee.employee.IsManager)\
            .annotate(average_score = Value(50,IntegerField()))
        logs = EvaluationLog.objects.filter(evaluation_year = selected_year, evaluation_month = selected_month, evaluatee__id = employee.id, staff_log = True)

        total_staff_score = 0
        total_staff_weight = 0

        for group in EvaluationCriteriaGroup.objects.filter(pk__in = criteria_groups).prefetch_related(Prefetch('org_group_weights',\
            queryset=EvaluationCriteriaGroupWeight.objects.filter(org_group = employee.employee.organization_group, weight__gt = 0), to_attr = "weight")):
            total_score_group = 0
            total_weight_group = 0
            for criteria in criterias.filter(group = group):
                if criteria.pk in logs.values_list('criteria__pk', flat = True):
                    sum_score = 0
                    sum_weight = 0
                    for log in logs.filter(criteria = criteria):
                        sum_score += log.score * log.relation_weight
                        sum_weight += log.relation_weight
                    if sum_weight > 0 :
                        criteria.average_score = sum_score / sum_weight
                    else:
                        criteria.average_score = 50
                total_score_group += criteria.average_score * criteria.weight
                total_weight_group += criteria.weight
            if total_weight_group > 0:
                total_staff_score += ( total_score_group / total_weight_group )* group.weight[0].weight
                total_staff_weight +=  group.weight[0].weight
            else:
                total_staff_score += ( 50 )* group.weight[0].weight
                total_staff_weight +=  group.weight[0].weight

        if total_staff_weight > 0:
            employee.average_staff_score = round(total_staff_score/ total_staff_weight)
        else:
            employee.average_staff_score = 50

    employees_list = [ { 'get_full_name': e.get_full_name(), 'average_staff_score': e.average_staff_score,\
         'average_score': e.average_score, 'organization_group': e.employee.organization_group.name} for e in employees]
    if order =='score' :
        context["employees"] = sorted(employees_list , key = lambda i : i['average_score'],reverse=True)
    elif order == 'staff_score':
        context["employees"] = sorted(employees_list , key = lambda i : i['average_staff_score'],reverse=True) 
    elif order == 'group_staff':
        context["employees"] = sorted(employees_list , key = lambda i : (i['organization_group'],i['average_staff_score']),reverse=True) 
    else:
        context["employees"] = sorted(employees_list , key = lambda i : (i['organization_group'],i['average_score']),reverse=True)
   

    return render(request, 'human_capitals/report.html', {'context':context})


    

@login_required(login_url='user:login') #redirect when user is not logged in
def upload_leave_excel(request):
    if(request.user.employee.organization_group.manager != request.user or request.user.employee.GetEmployeeParent != None) and (not request.user.employee.in_staff_group):
        raise PermissionDenied
    
    else:
        excel_file = request.FILES["human_capitals_leave_file_upload"]

        if not excel_file.name.endswith('.xlsx'):
            messages.warning(request, 'نوع فایل ارسالی معتبر نیست')
            return HttpResponseRedirect(request.GET['next'])

        try:
            file = openpyxl.load_workbook(excel_file)
        except:
            messages.warning(request, 'محتوی فایل قابل خواندن نیست')
            return HttpResponseRedirect(request.GET['next'])

        for row in file[file.sheetnames[0]].rows:

            try:
                
                if row[0].row > 2 :
                    personelnumber = int(row[1].value)
                    _user = Employee.objects.get(new_personelnumber = personelnumber).user
                    solar_date = str(row[0].value)
                    solar_year = int(solar_date[:4])
                    solar_month = int(solar_date[4:6])
                    worked = row[2].value
                    if row[3].value :
                        absent = int(row[3].value)
                    else:
                        absent = 0

                    if row[4].value:
                        mission = row[4].value
                    else:
                        mission = 0

                    if row[5].value :
                        leave_right = decimal.Decimal(row[5].value)
                    else :
                        leave_right = 0

                    if row[6].value :
                        leave_sick = int(row[6].value)
                    else:
                        leave_sick = 0

                    if row[7].value :
                        leave_reward = decimal.Decimal(row[7].value)
                    else:
                        leave_reward = 0

                    if  row[8].value :
                        leave_child = int(row[8].value)
                    else:
                        leave_child = 0

                    if row[9].value :
                        leave_die = int(row[9].value)
                    else:
                        leave_die = 0

                    if row[10].value :
                        undertime = int(row[10].value)
                    else:
                        undertime = 0

                    if row[11].value :
                        overtime_min = int(row[11].value)
                    else:
                        overtime_min = 0

                    if row[12].value :
                        overtime_hour = int(row[12].value)
                    else:
                        overtime_hour = 0

                    if row[13].value :
                        overtime_night = int(row[13].value)
                    else :
                        overtime_night = 0

                    if row[14].value:
                        quality = int(row[14].value)
                    else:
                        quality = 0

                    if row[15].value :
                        overtime_quality = int(row[15].value)
                    else:
                        overtime_quality = 0

                    if row[16].value :
                        teleworking = int(row[16].value)
                    else:
                        teleworking = 0

                    if row[17].value :
                        food = int(row[17].value)
                    else:
                        food = 0

                    if row[18].value :
                        overtime_limit = int(row[18].value)
                    else :
                        overtime_limit = 0

                    if row[19].value :
                        undertime_day = int(row[19].value)
                    else:
                        undertime_day = 0

                    if MonthStatistic.objects.filter(user = _user,year = solar_year, month = solar_month).exists():
                        MonthStatistic.objects.filter(user = _user,year = solar_year, month = solar_month).update(worked = worked,
                            absent = absent, mission = mission, leave_right = leave_right, leave_sick = leave_sick, leave_reward = leave_reward,
                            leave_child = leave_child, leave_die = leave_die, undertime = undertime, overtime_min = overtime_min,
                            overtime_hour = overtime_hour, overtime_night = overtime_night, quality = quality, overtime_quality = overtime_quality,
                            teleworking = teleworking, food = food, overtime_limit = overtime_limit, undertime_day = undertime_day)
                    else:
                        MonthStatistic.objects.create(user = _user,year = solar_year, month = solar_month, worked = worked,
                            absent = absent, mission = mission, leave_right = leave_right, leave_sick = leave_sick, leave_reward = leave_reward,
                            leave_child = leave_child, leave_die = leave_die, undertime = undertime, overtime_min = overtime_min,
                            overtime_hour = overtime_hour, overtime_night = overtime_night, quality = quality, overtime_quality = overtime_quality,
                            teleworking = teleworking, food = food, overtime_limit = overtime_limit, undertime_day = undertime_day)


            except:

                messages.warning(request, 'پردازش اطلاعات فایل با خطا مواجه شد')
        
        return HttpResponseRedirect(request.GET['next'])



# this function return reports list
@login_required(login_url='user:login') #redirect when user is not logged in
def SajjadReports(request):   #**kwargs
    
    as_user = request.user

    if as_user.employee.in_staff_group == False:
        data['message']="غیر معتبر است"
        return JsonResponse(data)


    request.session["activated_menu"]="human_capitals"
    context = {}
   
    context["users"] = User.objects.all().exclude(username='admin').exclude(employee=None).exclude(employee__organization_group=None).order_by('employee__organization_group__name')

   
    # u_id is selected user id in parameters    
    try:
        selected_user_id = int(request.GET.get("u_id",""))
    except:
        selected_user_id = as_user.id

    context["report_list_selected_user_id"] = selected_user_id
    selected_user = User.objects.get(id=selected_user_id)
    
    
    # f_day means "from day". used for select first day of a range
    try:
        selected_from_date = request.GET.get("f_day","")
        # format of f_day is hijri and need to be converted to gregorian
        selected_from_date = jdatetime.datetime.strptime(selected_from_date + " 00:00",'%Y/%m/%d %H:%M').togregorian()
    except:
        selected_from_date = datetime.datetime.combine(datetime.date.today() - datetime.timedelta(days=30) , datetime.datetime.min.time())
    context["report_list_selected_from_date"] = ConvertToSolarDate(selected_from_date)
    
    # t_day means "to day". used for select last day of a range
    try:
        selected_to_date = request.GET.get("t_day","")
        # format of t_day is hijri and need to be converted to gregorian
        selected_to_date =  jdatetime.datetime.strptime(selected_to_date + " 23:59",'%Y/%m/%d %H:%M').togregorian()    
    except:
        # this row create time format of today to  YYYY/MM/DD-23:59:59
        selected_to_date = datetime.datetime.combine(datetime.date.today(), datetime.time(23,59,59))
    context["report_list_selected_to_date"] = ConvertToSolarDate(selected_to_date)

    tasks_start=Task.started.filter(Q(user_assignee=selected_user)|Q(group_assignee__head=selected_user))
    context["tasks_start"] = tasks_start

    finished_tasks = Task.objects.filter(Q(user_assignee=selected_user)|Q(group_assignee__head=selected_user))\
        .filter(progress_complete_date__gte = selected_from_date)\
            .filter(progress_complete_date__lte = selected_to_date)

    context["finished_tasks"] = finished_tasks        

    return render(request, 'human_capitals/sajjad.html', {'context':context}) #,'report':report

