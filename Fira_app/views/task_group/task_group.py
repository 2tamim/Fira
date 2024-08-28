from django.shortcuts import render, redirect
from django.http import HttpResponse, Http404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from ...models import Task_Group,Task_Group_Member , Employee ,Notification
from django.http import JsonResponse
from ...Serializers.task_management_serializer import *
from django.db import transaction
from django.db.models import Subquery
from rest_framework.renderers import JSONRenderer
from django.core.exceptions import PermissionDenied
import datetime
from django.db.models import Q 

@login_required(login_url='user:login') #redirect when user is not logged in
def index(request):
    request.session["activated_menu"]="task_group"
    context={}
    _task_group=Task_Group.objects.filter(creator=request.user,cancelled=False)
    context['task_group']=_task_group
    member_in_task_group=Task_Group.objects.filter(Q(cancelled=False,pk__in=Subquery(Task_Group_Member.objects.filter(user=request.user).values('group_id')))|Q(cancelled=False,head=request.user))
    context['member_in_task_group']=member_in_task_group
    users=User.objects.filter(is_active=True).filter(pk__in=request.user.employee.GetAllChildrenUserId).exclude(username='admin').order_by('last_name')
    context['head']=users
    
    context["isManager"]=False
    if(request.user.employee.organization_group.manager==request.user):
        context["isManager"]=True
    return render(request, 'task_group/index.html', {'context':context})


@login_required(login_url='user:login') #redirect when user is not logged in
def add(request):
    data={}
    if request.method=="POST":
        if(request.user.employee.organization_group.manager!=request.user):
            data['message']="شما مجوز ایجاد کارگروه را ندارید"
            return JsonResponse(data)
        try:
            with transaction.atomic():
                task_group=Task_Group()
                task_group.name = request.POST["name"]
                task_group.creator=request.user
                task_group.head=User.objects.get(pk=request.POST["head"])
                
                if "autocancel" in request.POST:
                    task_group.autocancel=True
                else:
                    task_group.autocancel=False
                if "public" in request.POST:
                    task_group.public=True
                else:
                    task_group.public=False
                
                notification=Notification()
                notification.title="کارگروه جدید"
                notification.user=task_group.head
                notification.displaytime=datetime.datetime.now()
                notification.messages="شما به کارگروه "+ task_group.name + " اضافه شدید."
                notification.link="/task_group/"
                notification.save()

                task_group.head_notification=notification
                task_group.save()
                

                users=request.POST["users_id"].split(",")
                users=list(dict.fromkeys(users))
                if str(task_group.head.id) in users:
                    users.remove(str(task_group.head.id))
                for user in users:
                    task_group_member=Task_Group_Member()
                    task_group_member.group=task_group
                    task_group_member.user=User.objects.get(pk=int(user))
                    notification=Notification()
                    notification.title="کارگروه جدید"
                    notification.user=task_group_member.user
                    notification.displaytime=datetime.datetime.now()
                    notification.messages="شما به کارگروه "+ task_group.name + " اضافه شدید."
                    notification.link="/task_group/"
                    notification.save()
                    task_group_member.member_notification=notification
                    task_group_member.save()


                    
                data['message']="کارگروه با موفقیت ذخیره شد"
        except Exception as err:
            data['message']=err.args[0]
            print(err.args[0])
            
    return JsonResponse(data)


@login_required(login_url='user:login') #redirect when user is not logged in
def detail(request,id):
    data={}
    try:
        task_group=Task_Group.objects.get(pk=id)
        if task_group.head == request.user or task_group.creator == request.user or Task_Group_Member.objects.filter(group__pk=id).filter(Q(user=request.user)|Q(user__pk__in=request.user.employee.GetAllChildrenUserId )).count()>0  \
            or task_group.head.pk in request.user.employee.GetAllChildrenUserId or task_group.creator.pk in request.user.employee.GetAllChildrenUserId :
            pass
        else:
            data['error']="Access Denied"
            return JsonResponse(data)
        task_group=Task_GroupSerializer(Task_Group.objects.filter(pk=id), many=True)
        data["task_group"]=JSONRenderer().render(task_group.data).decode("utf-8")  #task_group.data
        
        task_group_member=Task_Group_MemberSerializer(Task_Group_Member.objects.filter(group_id=id), many=True)
        data["task_group_member"]=JSONRenderer().render(task_group_member.data).decode("utf-8")
        task_group_members_id=[]
        for membership in Task_Group_Member.objects.filter(group_id=id):
            task_group_members_id.append(membership.user.id)
        if not(Task_Group.objects.filter(creator=request.user) or (request.user.id in task_group_members_id) or (request.user ==task_group.head ) ):
            raise PermissionDenied
    except Exception as err:
        data['message']=err.args[0]
        print(err.args[0])
    return JsonResponse(data)

@login_required(login_url='user:login') #redirect when user is not logged in
def delete(request,id):
    data={}
    try:
        _task_group=Task_Group.objects.get(pk=id)
        if _task_group.creator !=request.user:
            raise PermissionDenied
        _task_group.cancelled=True
        _task_group.save()
        data["message"]="حذف کارگروه با موفقیت انجام شد"
       
    except Exception as err:
        data['message']="بروز خطا"
    
    try:
        notification=Notification.objects.get(pk=_task_group.head_notification.pk)
        notification.closed=True
        notification.save()
        task_group_member=Task_Group_Member.objects.filter(group=_task_group)
        for u in task_group_member:
            notification=Notification.objects.get(pk=u.member_notification.pk)
            notification.closed=True
            notification.save()
    except:
        pass
    return JsonResponse(data)


@login_required(login_url='user:login') #redirect when user is not logged in
def edit(request,id):
    data={}
    if request.method=="POST" :
        try:
            with transaction.atomic():
                _task_group=Task_Group.objects.get(pk=id)
                if _task_group.creator != request.user:
                    raise PermissionDenied
                _task_group.name=request.POST["detail_name"]
                _task_group.head=User.objects.get(pk=request.POST["detail_head"])
                notification=Notification.objects.get(pk=_task_group.head_notification.pk)
                if notification.user !=_task_group.head:
                    notification.user=_task_group.head
                    notification.closed=False
                    notification.displaytime=datetime.datetime.now()
                    notification.save()
        
                if "detail_autocancel" in request.POST:
                    _task_group.autocancel=True
                else:
                    _task_group.autocancel=False
                if "detail_public" in request.POST:
                    _task_group.public=True
                else:
                    _task_group.public=False
                _task_group.save()
                users=request.POST["detail_users_id"].split(",")

                users=list(dict.fromkeys(users))
                if str(_task_group.head.id) in users:
                    users.remove(str(_task_group.head.id))

                task_group_member=Task_Group_Member.objects.filter(group_id=id)

                for member in task_group_member:
                    if str(member.user_id) not in users:
                        member.delete()
                        notification=Notification.objects.get(pk=member.member_notification.pk)
                        notification.delete()
               

                # task_group_member=Task_Group_Member.objects.filter(group_id=id)
                finded=False
                for user in users:
                    try:
                        task_group_member=Task_Group_Member.objects.get(group_id=id,user_id=int(user))
                        finded=True
                    except :
                        finded=False
                    if finded==False:
                        task_group_member=Task_Group_Member()
                        task_group_member.group=_task_group
                        task_group_member.user=User.objects.get(pk=int(user))
                        notification=Notification()
                        notification.title="کارگروه جدید"
                        notification.user=task_group_member.user
                        notification.displaytime=datetime.datetime.now()
                        notification.messages="شما به کارگروه "+ _task_group.name + " اضافه شدید."
                        notification.link="/task_group/"
                        notification.save()
                        task_group_member.save()
                    
                data['message']="کارگروه با موفقیت ذخیره شد"
        except Exception as err:
            data['message']="بروز خطا"
    return JsonResponse(data)