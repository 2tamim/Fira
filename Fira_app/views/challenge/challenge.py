from urllib import request
from django.db.models import Q
from django.shortcuts import render, redirect
from django.http import HttpResponse, Http404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User

from ...models import Challenge,ChallengeComment,SolutionComment,ChallengeSolution,SameChallenge,SolutionVote, user_directory_path
import datetime
from jdatetime import datetime as jdt
from ...utilities.date_tools import ConvertToMiladi, ConvertToSolarDate,DateTimeDifference,ConvertTimeDeltaToStringTime
from django.http import JsonResponse
from ...Serializers.challenge_serializer import *
from django.core import serializers
from rest_framework.renderers import JSONRenderer
from django.core.exceptions import PermissionDenied
from django.db.models import Value,BooleanField
from django.contrib.postgres.search import TrigramSimilarity
from django.contrib.postgres.search import SearchVector, SearchQuery,SearchRank



# this function return reports list
@login_required(login_url='user:login') #redirect when user is not logged in
def ChallengeList(request):   #**kwargs
    _user = request.user

    request.session["activated_menu"]="challenge_list"
    context = {}
    context["user_id"] = request.user.pk
    sort_type = 1
    try:
        sort_type = int(request.GET.get("sort_type",""))
    except:
        sort_type = 1
    try:
        _solved = int(request.GET.get("solve",""))
        context["challenge_list_filter_solved_input"] = _solved
    except:
        _solved = 0
        context["challenge_list_filter_solved_input"] = _solved
        
    context["challenge_list_selected_challenge_sort"] = sort_type
    if _solved == 1 :
        public_challenges = Challenge.objects.filter(public_access = True, situation = 3)
        group_challlenges = Challenge.objects.filter(user__employee__organization_group = _user.employee.organization_group,public_access = False, situation = 3)
    else:
        public_challenges = Challenge.objects.filter(public_access = True)
        group_challlenges = Challenge.objects.filter(user__employee__organization_group = _user.employee.organization_group,public_access = False)

    challenges = public_challenges.union(group_challlenges,all=True)

    if sort_type == 1:
        sorted_challenges = challenges.order_by("created").reverse()
    elif sort_type == 2:
        sorted_challenges = challenges.order_by("importance")
    else:
        sorted_challenges = challenges

    context["challenges"] = sorted_challenges

    return render(request, 'challenge/list.html', {'context':context}) 

@login_required(login_url='user:login') #redirect when user is not logged in
def AddChallenge(request):   #**kwargs
    context={}
    context['success'] = False
    new_challenge = Challenge()
    if request.method == "POST":
        try:
            title = request.POST["challenge_add_modal_title_input"]
            content = request.POST["challenge_add_modal_content_input"]
            try:
                public_access = request.POST["challenge_add_modal_public_access_input"]
                public_access = True
            except:
                public_access = False
            importance = int(request.POST["challenge_add_importance_input"])
        

            new_challenge.title = title
            new_challenge.content = content
            new_challenge.public_access = public_access
            new_challenge.importance = importance
            new_challenge.user = request.user
            new_challenge.situation = 1
            new_challenge.save()

            context["message"]="افزودن چالش با موفقیت انجام شد"
        except:
            context["message"]="خطا در افزدودن چالش"
    return JsonResponse(context)


@login_required(login_url='user:login') #redirect when user is not logged in
def ChallengeDetail(request,challenge_id):
    data={}
    _user = request.user
    try:
        _challenge = Challenge.objects.get(pk=int(challenge_id))
        this_user = request.user
        if  not _challenge.public_access and this_user.employee.organization_group != _challenge.user.employee.organization_group:
            raise PermissionDenied
        _challenge_serilize = ChallengeSerializer(_challenge)
        data["challenge"] = JSONRenderer().render(_challenge_serilize.data).decode("utf-8")

        if _challenge.user == this_user:
            data["challenge_writer"] = 1
        else:
            data["challenge_writer"] = 0

        try:
            same_challenge = SameChallenge.objects.get(challenge=_challenge, user=_user)
            if same_challenge or _user == _challenge.user:
                data["same_challenge"] = 1
            else:
                data["same_challenge"] = 0
        except:
            if _user == _challenge.user:
                data["same_challenge"] = 1
            else:
                data["same_challenge"] = 0
    except Exception as err:
        data['message']=err.args[0]
    return JsonResponse(data)

@login_required(login_url='user:login') #redirect when user is not logged in
def HaveSameChallenge(request,challenge_id):
    
    data={}
    try:
        _challenge = Challenge.objects.get(pk=int(challenge_id))
        this_user = request.user
        if  not _challenge.public_access and this_user.employee.organization_group != _challenge.user.employee.organization_group:
            raise PermissionDenied
        try:
            _same_challenge_list = SameChallenge.objects.filter(challenge=_challenge , user = this_user)
        except:
            data['message']=err.args[0]
            return JsonResponse(data)
            
        if _challenge.user != this_user and  len(_same_challenge_list) == 0: 
            _same_challenge = SameChallenge()
            _same_challenge.challenge = _challenge
            _same_challenge.user = this_user
            _same_challenge.save()
            data["value"] = _challenge.SameChallengeNumber
            data['message'] = "انجام شد"
        else:
            data["value"] = _challenge.SameChallengeNumber
            data["message"] =  "قبلا ثبت شده است"


    except Exception as err:
        data['message']=err.args[0]
    return JsonResponse(data)

@login_required(login_url='user:login') #redirect when user is not logged in
def AddChallengeComment(request,challenge_id):
    data={}
    try:
        _challenge = Challenge.objects.get(pk=int(challenge_id))
        this_user = request.user
        if  not _challenge.public_access and this_user.employee.organization_group != _challenge.user.employee.organization_group:
            raise PermissionDenied
        challenge_comment = ChallengeComment()
        challenge_comment.challenge = _challenge
        challenge_comment.user = request.user
        challenge_comment.content = request.POST["challenge_list_detail_body_new_comment_input"]
        challenge_comment.save()
        serilized_comment = ChallengeCommentSerializer(challenge_comment)
        data["comment"] = JSONRenderer().render(serilized_comment.data).decode("utf-8")
        data["comment_number"] = _challenge.CommentsNumber
        data['message'] = "ثبت شد"
    except Exception as err:
        data['message']=err.args[0]
    return JsonResponse(data)

@login_required(login_url='user:login') #redirect when user is not logged in
def AddSolution(request):
    data={}
    if request.method=="POST":
        challenge_id = int(request.POST["solution_add_challenge_id"])
    try:
        _challenge = Challenge.objects.get(pk=int(challenge_id))
        this_user = request.user
        if  not _challenge.public_access and this_user.employee.organization_group != _challenge.user.employee.organization_group:
            raise PermissionDenied

        _solution = ChallengeSolution()
        _solution.user = request.user
        _solution.content = request.POST["solution_add_modal_content_input"]
        _solution.challenge = _challenge
        _solution.agree_vote = 0
        _solution.disagree_vote = 0
        _solution.confirmed_by_auther = False
        _solution.save()
        if _challenge.situation == 1:
            _challenge.situation = 2
            _challenge.save()
        serilized_solution = ChallengeSolutionSerializer(_solution)
        data["solution"] = JSONRenderer().render(serilized_solution.data).decode("utf-8")
        data["solution_number"] =  _challenge.SolutionsNumber
        data["challenge_situation"] =  _challenge.situation
        data["challenge_id"] =  _challenge.id
        if _challenge.user == this_user:
            data["challenge_writer"] = 1
        else:
            data["challenge_writer"] = 0
        data['message'] = "ثبت شد"
    except Exception as err:
        data['errormessage']=err.args[0]
    return JsonResponse(data)


@login_required(login_url='user:login') #redirect when user is not logged in
def AddSolutionComment(request,solution_id):
    data={}
    try:
        _solution = ChallengeSolution.objects.get(pk = solution_id)
        _challenge = _solution.challenge
        this_user = request.user
        if  not _challenge.public_access and this_user.employee.organization_group != _challenge.user.employee.organization_group:
            raise PermissionDenied
        solution_comment = SolutionComment()
        solution_comment.solution = _solution
        solution_comment.content = request.POST["solutichallenge_list_detail_solutions_new_comment_input_"+str(solution_id)]
        solution_comment.user = request.user
        solution_comment.save()
        serilized_comment = SolutionCommentSerializer(solution_comment)
        data["comment"] = JSONRenderer().render(serilized_comment.data).decode("utf-8")
        data['message'] = "ثبت شد"
    except Exception as err:
        data['message']=err.args[0]
    return JsonResponse(data)

@login_required(login_url='user:login') #redirect when user is not logged in
def GetSolutionVotes(request ,solution_id ,vote_value):
    data={}
    try:
        _solution = ChallengeSolution.objects.get(pk = solution_id)
        _challenge = _solution.challenge
        this_user = request.user
        if  not _challenge.public_access and this_user.employee.organization_group != _challenge.user.employee.organization_group:
            raise PermissionDenied
        vote_value = int(vote_value)
        try:
            solution_vote = SolutionVote.objects.get(solution = _solution , user = request.user)
            if  solution_vote.value == 1 and vote_value == 1:
                data['message']="قبلا رای  مثبت داده اید" 

            elif solution_vote.value == -1 and vote_value == 1:
                solution_vote.value = 1
                solution_vote.save()
                data['message']="انجام شد"

            elif  solution_vote.value == -1 and vote_value == 2:
                data['message']="قبلا رای منفی داده اید" 

            elif solution_vote.value == 1 and vote_value == 2:
                solution_vote.value = -1
                solution_vote.save()
                data['message']="انجام شد"
            else:
                pass
            

        except:
            solution_vote = SolutionVote()
            solution_vote.solution = _solution
            solution_vote.user = request.user
            if vote_value == 1:
                solution_vote.value = 1
                solution_vote.save()
            elif vote_value == 2:
                solution_vote.value = -1
                solution_vote.save()
        data["agree_vote"]= _solution.AgreeVote 
        data["disagree_vote"]= _solution.DisAgreeVote 
    except Exception as err:
        data['message']=err.args[0]
    return JsonResponse(data)

@login_required(login_url='user:login') #redirect when user is not logged in
def ConfirmSolution(request,solution_id):
    data={}
    try:
        _solution = ChallengeSolution.objects.get(pk = solution_id)
        _challenge = _solution.challenge
        this_user = request.user
        if  not _challenge.public_access and this_user.employee.organization_group != _challenge.user.employee.organization_group:
            raise PermissionDenied
        if this_user != _challenge.user:
            raise PermissionDenied
        _solution.confirmed_by_auther = True
        _solution.save()
        _challenge.situation = 3
        _challenge.save()
        data["confirmed_by_auther"] = 1
        data["solution_id"] = solution_id
        data["challenge_situation"] = _challenge.situation
        data["challenge_id"] = _challenge.id
        data['message'] = "تایید شد"
    except Exception as err:
        data['message'] = err.args[0]
    return JsonResponse(data)


@login_required(login_url='user:login') #redirect when user is not logged in
def UnConfirmSolution(request,solution_id):
    data={}
    try:
        _solution = ChallengeSolution.objects.get(pk = solution_id)
        _challenge = _solution.challenge
        this_user = request.user
        if  not _challenge.public_access and this_user.employee.organization_group != _challenge.user.employee.organization_group:
            raise PermissionDenied
        if this_user != _challenge.user:
            raise PermissionDenied
        _solution.confirmed_by_auther = False
        _solution.save()

        _solutions = ChallengeSolution.objects.filter(challenge = _challenge , confirmed_by_auther = True)
        if len(_solutions) > 0:
            _challenge.situation = 3
            _challenge.save()
        else:
            _challenge.situation = 2
            _challenge.save()


        data["confirmed_by_auther"] = 0
        data["solution_id"] = solution_id
        data["challenge_situation"] = _challenge.situation
        data["solution_number"] = _challenge.SolutionsNumber
        data["challenge_id"] = _challenge.id
        data['message'] = "رد شد"
    except Exception as err:
        data['message'] = err.args[0]
    return JsonResponse(data)









       