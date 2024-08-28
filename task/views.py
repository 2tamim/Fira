from django.shortcuts import get_list_or_404, get_object_or_404
from django.db.models import Q
from django.urls import reverse
from rest_framework import generics, mixins, viewsets, status, views
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, BasePermission, AllowAny, IsAdminUser
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.renderers import JSONRenderer
from utils.pagination import NormalPagesPagination
import datetime
from django.db import transaction
from .serializers import *
from user.models import Notification
from django.core.files.uploadedfile import InMemoryUploadedFile
# Create your views here.
from django.db.models import Avg,Sum



class KanbanTasksView(generics.ListAPIView):

    permission_classes = [IsAuthenticated]
    serializer_class = TaskDetailSerializer

    def get_queryset(self):
        # Find user based on ?user=<user_id> query param
        if self.request.query_params.get('user',False) and int(self.request.query_params.get('user',None)):
            try:
                if int(self.request.query_params.get('user')) in self.request.user.employee.all_children_user_id:
                    user = User.objects.get(id=int(self.request.query_params.get('user')))
                else:
                    user = self.request.user
            except:
                user = self.request.user
        else:
            user = self.request.user

        if user.employee.is_manager :
            request_pool = Task.objects.filter(task_type__is_request=True,user_assignee=user).exclude(cancelled=True).exclude(confirmed=True)
        else:
            request_pool = Task.objects.filter(task_type__is_request=True,user_assignee=user.employee.parent).exclude(cancelled=True).exclude(confirmed=True)

        requests = Task_Assign_Request.objects.filter(task__creator = user.employee.organization_group.manager).values_list('task__id', flat=True)
        return Task.objects.filter(Q(user_assignee = user,approved=True) |Q(executor = user) |\
            (Q(user_assignee=None,group_assignee=None, creator=user.employee.organization_group.manager)&~Q(id__in=requests))|\
                    Q(approved=False, creator__in=user.employee.direct_children_user_id)|Q(approved=False, creator=user))\
                        .exclude(cancelled=True).exclude(confirmed=True) | request_pool


class TaskDetailUpdatePermission(BasePermission):

    def has_object_permission(self, request, view, obj=None):
        if request.method == "GET":
            requests = Task_Assign_Request.objects.filter(task = obj,user = request.user).values_list('task__id', flat=True)
            verification_needed = Task_Verification_Log.objects.filter(task = obj, verifier_locumtenens=request.user, verifier=request.user)

            if obj.creator == request.user or obj.user_assignee == request.user or \
                obj.creator.id in request.user.employee.all_children_user_id or obj.user_assignee.id in request.user.employee.all_children_user_id or\
                    (obj.creator == request.user.employee.organization_group.manager and obj.user_assignee==None and obj.group_assignee==None and obj.task_assign_requests.all().count()==0) or\
                        requests.count() > 0 or verification_needed.count() > 0:
                return True
            else:
                return False
        if request.method == "PUT" :
            if obj.creator == request.user or (obj.creator.employee and obj.creator.employee.parent == request.user):
                return True
            else:
                return False


class TaskRetrieveUpdateView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated, TaskDetailUpdatePermission]
    queryset = Task.objects.all()

    def get_serializer_class(self):
        if self.request.method == "GET":
            return TaskDetailSerializer
        if self.request.method == "PUT":
            return TaskUpdateSerializer
        return TaskDetailSerializer

    def update(self, request, *args, **kwargs):
        try:
            old = self.get_object()

            if 'name' in request.data.keys() and (len(request.data['name']) < 1 or request.data['name'] == None) :
                return Response(status=status.HTTP_411_LENGTH_REQUIRED,data='نام کار اجباری است.')

            if 'task_parent' in request.data.keys() and request.user.employee.parent and request.data['task_parent'] == None :
                return Response(status=status.HTTP_424_FAILED_DEPENDENCY,data='انتخاب کار والد اجباری است.')

            if 'user_assignee' in request.data.keys() and (not request.user.employee.is_manager ) and request.data['user_assignee'] == None :
                return Response(status=status.HTTP_424_FAILED_DEPENDENCY,data='شما مجاز به تعریف کار بدون مسئول نیستید.')

            if 'user_assignee' in request.data.keys() and int(request.data['user_assignee']) != old.user_assignee_id and\
                old.children.all().count() > 0 :
                return Response(status=status.HTTP_403_FORBIDDEN, data='تغییر مسئول کاری که زیرمجموعه آن کارهای جدید تعریف شده مجاز نیست..')

            if 'user_assignee' in request.data.keys() and request.data['user_assignee'] != None and int(request.data['user_assignee']) != request.user.id and \
                not(int(request.data['user_assignee']) in request.user.employee.direct_children_user_id):
                return Response(status=status.HTTP_403_FORBIDDEN, data='شما مجاز به سپردن کار به این کاربر نیستید.')

            if  'current' in request.data.keys() and request.data['current'] == 'false' and \
                not ('startdate' in request.data.keys() and 'enddate' in request.data.keys()) :
                return Response(status=status.HTTP_403_FORBIDDEN, data='کارها بایستی به صورت جاری تعریف شوند یا دارای تاریخ شروع و پایان باشند.')

            serializer = self.get_serializer(data = request.data)
            if serializer.is_valid():
                validated_data = serializer.validated_data
                if 'task_parent' in request.data.keys() and validated_data['task_parent'].user_assignee != request.user :
                    return Response(status=status.HTTP_403_FORBIDDEN, data='امکان تعریف کار زیرمجموعه برای کاری که مسئول آن نیستید وجود ندارد.')

                if 'current' in request.data.keys() :
                    current_new_value = validated_data['current']
                else:
                    current_new_value = old.current
                
                if 'task_parent' in request.data.keys():
                    parent_currnet_new_value = validated_data['task_parent'].current
                    parent_startdate = validated_data['task_parent'].startdate
                    parent_enddate = validated_data['task_parent'].enddate
                else:
                    parent_currnet_new_value = old.task_parent.current
                    parent_startdate = old.task_parent.startdate
                    parent_enddate = old.task_parent.enddate

                if current_new_value and not parent_currnet_new_value:
                    return Response(status=status.HTTP_403_FORBIDDEN, data='امکان تعریف کار جاری فقط به صورت زیرمجموعه کارهای جاری وجود دارد.')

                if  'current' in request.data.keys() and request.data['current'] == 'false' and \
                    (validated_data['startdate'] > validated_data['enddate'] or \
                        validated_data['startdate'] < parent_startdate or\
                            validated_data['enddate'] < parent_enddate):
                    return Response(status=status.HTTP_409_CONFLICT, data='تاریخ های شروع و پایان ارسالی با همدیگر یا با تاریخ های کار والد همخوانی ندارند.')
                
            else:
                return Response(status=status.HTTP_400_BAD_REQUEST, data='اطلاعات وارد شده معتبر نیست.')

            updated = super(TaskRetrieveUpdateView, self).update(request, *args, **kwargs)
            new_task = updated.data.serializer.instance

            if new_task.startdate_notification == None  and (not new_task.current):
                start_notif = Notification.objects.create(
                    title='شروع کار '+ new_task.name,
                    user=new_task.user_assignee,
                    displaytime=new_task.startdate + datetime.timedelta(days=1),
                    messages="این کار بایستی در تاریخ " + new_task.PersianStartDate + " شروع می شد.",
                    link=reverse("api_task:kanban_tasks")
                )
                new_task.startdate_notification = start_notif
                new_task.save()

                end_notif = Notification.objects.create(
                    title='اتمام کار '+ new_task.name,
                    user=new_task.user_assignee,
                    displaytime=new_task.enddate + datetime.timedelta(days=1),
                    messages="این کار بایستی در تاریخ " + new_task.PersianStartDate + " تمام می شد.",
                    link=reverse("api_task:kanban_tasks")
                )
                new_task.enddate_notification = end_notif
                new_task.save()

            if new_task.startdate_notification != None and new_task.current:
                new_task.startdate_notification.delete()
                new_task.enddate_notification.delete()

            if new_task.startdate_notification != None and ( not new_task.current) and\
                'startdate' in request.data.keys() and 'enddate' in request.data.keys():
                new_task.startdate_notification.displaytime=new_task.startdate + datetime.timedelta(days=1)
                new_task.startdate_notification.save()
                new_task.enddate_notification.displaytime=new_task.enddate + datetime.timedelta(days=1)
                new_task.enddate_notification.save()


            response = {
                'status': 'success',
                'code': status.HTTP_200_OK,
                'message': 'Task updated successfully',
                'data': TaskDetailSerializer(new_task).data
            }
            return Response(response)
        except Exception as ex:
            return Response(status=status.HTTP_400_BAD_REQUEST, data=str(ex))


class TaskProgressUpdatePermission(BasePermission):
    def has_object_permission(self, request, view, obj=None):
        
        if obj.creator == request.user or obj.user_assignee == request.user or obj.executor == request.user:
            return True
        else:
            return False


class TaskProgressUpdateView(generics.UpdateAPIView):
    serializer_class = ChangeTaskProgressSerializer
    queryset = Task.objects.all()
    lookup_field = 'pk'
    permission_classes = [IsAuthenticated, TaskProgressUpdatePermission]


    def update(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        if serializer.is_valid():
            self.object =self.get_object()
            if self.object.wait == True:
                response = {
                    'status': 'failure',
                    'code': status.HTTP_400_BAD_REQUEST,
                    'message': 'Can`t update progress of waiting task',
                    'data': []
                }
                return Response(response)
            if request.data.get('progress') >= 0 and request.data.get('progress') <= 100 and self.object.approved == True:
                self.object.progress = request.data.get('progress')
                self.object.save()
                response = {
                    'status': 'success',
                    'code': status.HTTP_200_OK,
                    'message': 'Progress updated successfully',
                    'data': []
                }
                return Response(response)
            else:
                response = {
                    'status': 'failure',
                    'code': status.HTTP_400_BAD_REQUEST,
                    'message': 'Progress must be between 0 and 100 and task must be approved',
                    'data': []
                }
                return Response(response)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class TaskCreateView(generics.CreateAPIView):
    queryset = Task.objects.all()
    serializer_class = TaskCreateSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        try:
            request.data._mutable = True
            request.data['creator'] = request.user.id
            if not request.user.employee.is_manager :
                request.data['approved'] = False

            files=[]
            if 'task_attachments' in request.data.keys():
                request.data['task_attachments']=None
                files = request.FILES.getlist("task_attachments")

            if len(request.data['user_assignee']) > 0 :
                request.data['assign_status'] = 1

            if len(request.data['task_priority']) > 0  and int(request.data['task_priority']) and \
                (int(request.data['task_priority']) < 1 or int(request.data['task_priority']) > 3) :
                return Response(status=status.HTTP_403_FORBIDDEN,data='اولویت کار بایستی بین 1 تا 3 باشد.')

            if len(request.data['name']) < 1 :
                return Response(status=status.HTTP_411_LENGTH_REQUIRED,data='نام کار اجباری است.')

            if request.user.employee.parent and len(request.data['task_parent']) < 1 :
                return Response(status=status.HTTP_424_FAILED_DEPENDENCY,data='انتخاب کار والد اجباری است.')

            if (not request.user.employee.is_manager ) and len(request.data['user_assignee']) < 1 :
                return Response(status=status.HTTP_424_FAILED_DEPENDENCY,data='شما مجاز به تعریف کار بدون مسئول نیستید.')

            if len(request.data['user_assignee']) > 0 and int(request.data['user_assignee']) != request.user.id and \
                not(int(request.data['user_assignee']) in request.user.employee.direct_children_user_id):
                return Response(status=status.HTTP_403_FORBIDDEN, data='شما مجاز به سپردن کار به این کاربر نیستید.')

            if ( not request.data['current'] == 'true') and (len(request.data['startdate']) < 1 or len(request.data['enddate']) < 1):
                return Response(status=status.HTTP_403_FORBIDDEN, data='کارها بایستی به صورت جاری تعریف شوند یا دارای تاریخ شروع و پایان باشند.')

            serializer = self.get_serializer(data = request.data)
            if serializer.is_valid():
                validated_data = serializer.validated_data
                if validated_data['task_parent'].user_assignee != request.user :
                    return Response(status=status.HTTP_403_FORBIDDEN, data='امکان تعریف کار زیرمجموعه برای کاری که مسئول آن نیستید وجود ندارد.')

                if validated_data['current'] and not validated_data['task_parent'].current:
                    return Response(status=status.HTTP_403_FORBIDDEN, data='امکان تعریف کار جاری فقط به صورت زیرمجموعه کارهای جاری وجود دارد.')

                if  not validated_data['current'] and (validated_data['task_parent'].current or \
                    (validated_data['startdate'] > validated_data['enddate'] or \
                        validated_data['startdate'] < validated_data['task_parent'].startdate or\
                            validated_data['enddate'] < validated_data['task_parent'].enddate)):
                    return Response(status=status.HTTP_409_CONFLICT, data='تاریخ های شروع و پایان ارسالی با همدیگر یا با تاریخ های کار والد همخوانی ندارند.')
                
                

            created = super(TaskCreateView, self).create(request, *args, **kwargs)
            new_task = created.data.serializer.instance

            if new_task.assign_status == 1  and (not new_task.current):
                start_notif = Notification.objects.create(
                    title='شروع کار '+ new_task.name,
                    user=new_task.user_assignee,
                    displaytime=new_task.startdate + datetime.timedelta(days=1),
                    messages="این کار بایستی در تاریخ " + new_task.PersianStartDate + " شروع می شد.",
                    link=reverse("api_task:kanban_tasks")
                )
                new_task.startdate_notification = start_notif
                new_task.save()

                end_notif = Notification.objects.create(
                    title='اتمام کار '+ new_task.name,
                    user=new_task.user_assignee,
                    displaytime=new_task.enddate + datetime.timedelta(days=1),
                    messages="این کار بایستی در تاریخ " + new_task.PersianStartDate + " تمام می شد.",
                    link=reverse("api_task:kanban_tasks")
                )
                new_task.enddate_notification = end_notif
                new_task.save()

            for _file in files:
                Task_Attachment.objects.create(
                    name=_file.name, 
                    task=new_task, 
                    attachment_file=_file, 
                    filename=_file.name, 
                    user=request.user)

            response = {
                'status': 'success',
                'code': status.HTTP_200_OK,
                'message': 'Task created successfully',
                'data': TaskDetailSerializer(new_task).data
            }
            return Response(response)
        except Exception as ex:
            return Response(status=status.HTTP_400_BAD_REQUEST, data=str(ex))


class SubtaskPermission(BasePermission):
    def has_permission(self, request, view):
        task = Task.objects.get(pk=request.parser_context['kwargs']['task_id'])
        if task.user_assignee == request.user :
            return True
        return False

    def has_object_permission(self, request, view, obj=None):
        task = Task.objects.get(pk=request.parser_context['kwargs']['task_id'])
        if request.method == "GET":
            requests = Task_Assign_Request.objects.filter(task = task,user = request.user).values_list('task__id', flat=True)
            verification_needed = Task_Verification_Log.objects.filter(task = task, verifier_locumtenens=request.user, verifier=request.user)

            if task.creator == request.user or task.user_assignee == request.user or \
                task.creator.id in request.user.employee.all_children_user_id or task.user_assignee.id in request.user.employee.all_children_user_id or\
                    (creator==user.employee.organization_group.manager and user_assignee==None and group_assignee==None and task.task_assign_requests.all().count()==0) or\
                        requests.count() > 0 or verification_needed.count() > 0:
                return True
            else:
                return False
        else :
            if task.user_assignee == request.user :
                return True
            return False


class SubtaskViewset(viewsets.ModelViewSet):
    serializer_class = SubtaskSerializer
    permission_classes = [IsAuthenticated & SubtaskPermission]

    def get_queryset(self):
        return Subtask.objects.filter(task_id = self.kwargs['task_id'])

    def create(self, request, *args, **kwargs):
        task = Task.objects.get(pk = self.kwargs['task_id'])
        if task.subtasks.filter(name=request.data["name"]).count() > 0:
            return Response(status=status.HTTP_409_CONFLICT, data='کار جانبی با این نام وجود دارد.')
        new_subtask = task.subtasks.create(name = request.data["name"])
        response = {
            'status': 'success',
            'code': status.HTTP_200_OK,
            'message': 'Subtask created successfully',
            'data': SubtaskSerializer(new_subtask).data
        }
        return Response(response)

    def update(self, request, *args, **kwargs):
        # if 'done_time' in request.data.keys() and validated_data['task_parent'].user_assignee != request.user :
        #         return Response(status=status.HTTP_403_FORBIDDEN, data='امکان تعریف کار زیرمجموعه برای کاری که مسئول آن نیستید وجود ندارد.')
        old_done = self.get_object().done
        

        updated = super(SubtaskViewset, self).update(request, *args, **kwargs)
        new_subtask = updated.data.serializer.instance

        if 'done' in request.data.keys() and request.data['done'] == True and old_done == False:
            new_subtask.done_time = datetime.datetime.now()
            new_subtask.save()

        if 'done' in request.data.keys() and request.data['done'] == False and old_done == True:
            new_subtask.done_time = None
            new_subtask.save()

        response = {
            'status': 'success',
            'code': status.HTTP_200_OK,
            'message': 'Subtask updated successfully',
            'data': SubtaskSerializer(new_subtask).data
        }
        return Response(response)


class TaskAttachmentAndCommentPermission(BasePermission):
    def has_permission(self, request, view):
        task = Task.objects.get(pk=request.parser_context['kwargs']['task_id'])
        if task.user_assignee == request.user or task.creator == request.user :
            return True
        return False

    def has_object_permission(self, request, view, obj=None):
        task = Task.objects.get(pk=request.parser_context['kwargs']['task_id'])
        if request.method == "GET":
            requests = Task_Assign_Request.objects.filter(task = task,user = request.user).values_list('task__id', flat=True)
            verification_needed = Task_Verification_Log.objects.filter(task = task, verifier_locumtenens=request.user, verifier=request.user)

            if task.creator == request.user or task.user_assignee == request.user or \
                task.creator.id in request.user.employee.all_children_user_id or task.user_assignee.id in request.user.employee.all_children_user_id or\
                    (creator==user.employee.organization_group.manager and user_assignee==None and group_assignee==None and task.task_assign_requests.all().count()==0) or\
                        requests.count() > 0 or verification_needed.count() > 0:
                return True
            else:
                return False
        else :
            if task.user_assignee == request.user or task.creator == request.user :
                return True
            return False


class TaskAttachmentViewset(viewsets.ModelViewSet):
    serializer_class = TaskAttachmentSerializer
    permission_classes = [IsAuthenticated & TaskAttachmentAndCommentPermission]

    def get_queryset(self):
        return Task_Attachment.objects.filter(task_id = self.kwargs['task_id'])

    def create(self, request, *args, **kwargs):
        task = Task.objects.get(pk = self.kwargs['task_id'])
        
        files = request.FILES.getlist("task_attachments")
        for _file in files:
            Task_Attachment.objects.create(name=_file.name, task=task, attachment_file=_file, filename=_file.name, user=request.user)
        response = {
            'status': 'success',
            'code': status.HTTP_200_OK,
            'message': 'Attachment created successfully',
            'data': TaskAttachmentSerializer(task.task_attachments.all(), many=True).data
        }
        return Response(response)

    def update(self, request, *args, **kwargs):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED, data='امکان ویرایش فایل های پیوست شده وجود ندارد.')

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.user != request.user:
            return Response(status=status.HTTP_403_FORBIDDEN, data='شما مجاز به پاک کردن اسنادی هستید که خودتان پیوست کردید.')
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)


class TaskCommentViewset(viewsets.ModelViewSet):
    serializer_class = TaskCommentSerializer
    permission_classes = [IsAuthenticated & TaskAttachmentAndCommentPermission]

    def get_queryset(self):
        return TaskComment.objects.filter(task_id = self.kwargs['task_id'])

    def update(self, request, *args, **kwargs):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED, data='امکان ویرایش نظرات ثبت شده وجود ندارد.')

    def create(self, request, *args, **kwargs):
        task = Task.objects.get(pk = self.kwargs['task_id'])
        
        content = request.data['content']
        comment = TaskComment.objects.create(content=content, task=task, user=request.user)
        response = {
            'status': 'success',
            'code': status.HTTP_200_OK,
            'message': 'Attachment created successfully',
            'data': TaskCommentSerializer(comment).data
        }
        return Response(response)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.user != request.user:
            return Response(status=status.HTTP_403_FORBIDDEN, data='شما مجاز به پاک کردن نظراتی هستید که خودتان ثبت کردید.')
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)


class TaskStatesListView(generics.ListAPIView):
    serializer_class = TaskTypeStateSerializer
    permission_classes = [IsAuthenticated, TaskDetailUpdatePermission]
    
    
    def get_queryset(self):
        task = Task.objects.get(pk = self.kwargs['task_id'])
        return Task_Type_State.objects.filter(task_type = task.task_type)


class RequestTypeListView(generics.ListAPIView):
    serializer_class = TaskTypeSerializer
    permission_classes = [IsAuthenticated]
    queryset = Task_Type.objects.filter(is_request=True)


class RequestCreateListView(generics.ListAPIView):
    serializer_class = TaskDetailSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        task_requests=Task_Assign_Request.objects.filter(status=None, task__user_assignee=None,notification_status=None).exclude(need_verification=True).exclude(task__assign_status__lte = 2).exclude(task__cancelled = True).exclude(task__confirmed = True).exclude(task__public = True).filter(Q(user=self.request.user)|Q(user__id__in=self.request.user.employee.all_children_user_id))
        task_verification_log = Task_Verification_Log.objects.filter(pk = -1)
        if self.request.user.employee.organization_group.locumtenens_active:
            task_verification_log = Task_Verification_Log.objects.filter(Q(verifier=self.request.user)|Q(verifier_locumtenens=self.request.user)).exclude(verified=None)    
        else:
            task_verification_log = Task_Verification_Log.objects.filter(verifier=self.request.user).exclude(verified=None)

        return  Task.objects.exclude(assign_status__lte = 2).exclude(public = True).filter(Q(creator=self.request.user)|Q(pk__in=task_requests.values_list('task', flat = True))|Q(pk__in=task_verification_log.values_list('task', flat = True))).order_by('-pk')

    def post(self,request, format=None):
        task_info = request.data.copy()
        task_info['creator'] = request.user.id

        if len(task_info['name']) < 1 :
            return Response(status=status.HTTP_411_LENGTH_REQUIRED,data='نام کار اجباری است.')

        if  len(task_info['enddate']) < 1:
            task_info['current'] = 'true'
        else:
            task_info['current'] = 'false'
            task_info['startdate'] = datetime.date.today().strftime("%Y-%m-%d")

        serializer = TaskCreateSerializer(data = task_info)
        if serializer.is_valid():
            validated_data = serializer.validated_data
        else:
            return Response(status=status.HTTP_400_BAD_REQUEST,data='Invalid task info')

        if validated_data["task_type"] == None:
            return Response(status=status.HTTP_411_LENGTH_REQUIRED,data='نوع درخواست اجباری است.')

        task_type = validated_data["task_type"]

        for prop in task_type.task_type_property.all().exclude(slug = None):
            if not prop.slug in task_info.keys():
                return Response(status=status.HTTP_400_BAD_REQUEST,data='Invalid task info: '+ prop.slug)
            if type(task_info[prop.slug]) == InMemoryUploadedFile or len(task_info[prop.slug].strip()) > 0:
                if prop.value_type==1  and not \
                    TaskPropertyNumSerializer(data={'task_type_property':TaskTypePropertySerializer(prop).data,\
                                                    'value':task_info[prop.slug]}).is_valid():    # 1 = Task_Property_Num
                    return Response(status=status.HTTP_400_BAD_REQUEST,data='Invalid property value: '+ prop.slug)
                if prop.value_type==2 and not \
                    TaskPropertyTextSerializer(data={'task_type_property':TaskTypePropertySerializer(prop).data,\
                                                    'value':task_info[prop.slug]}).is_valid():    # 2 = Task_Property_Text
                    return Response(status=status.HTTP_400_BAD_REQUEST,data='Invalid property value: '+ prop.slug)
                if prop.value_type==3 and not \
                    TaskPropertyDateSerializer(data={'task_type_property':TaskTypePropertySerializer(prop).data,\
                                                    'value':task_info[prop.slug]}).is_valid():    # 3 = Task_Property_date
                    return Response(status=status.HTTP_400_BAD_REQUEST,data='Invalid property value: '+ prop.slug)
                if prop.value_type==4 and not \
                    TaskPropertyFileSerializer(data={'task_type_property':TaskTypePropertySerializer(prop).data,\
                                                    'value':task_info[prop.slug], 'filename': task_info[prop.slug].name}).is_valid():    # 4 = Task_Property_File
                    return Response(status=status.HTTP_400_BAD_REQUEST,data='Invalid property value: '+ prop.slug)
                if prop.value_type==5 and not \
                    TaskPropertyBoolSerializer(data={'task_type_property':TaskTypePropertySerializer(prop).data,\
                                                    'value':task_info[prop.slug]}).is_valid():    # 5 = Task_Property_Bool
                    return Response(status=status.HTTP_400_BAD_REQUEST,data='Invalid property value: '+ prop.slug)

        if task_type.needs_verfication and task_type.verifications.count() == 0:
            return Response(status=status.HTTP_400_BAD_REQUEST,data='Task type needs verification but no verificcation defined')
        
        if (not task_type.auto_request) or task_type.auto_requests.count() == 0:
            return Response(status=status.HTTP_400_BAD_REQUEST,data='Task type must have auto requests enabled and defined')

        if (task_type.froce_assign_request and (task_type.auto_requests.count() == 0 or not task_type.auto_request )) :
            return Response(status=status.HTTP_400_BAD_REQUEST,data='When using force assign , auto  request must be enabled and defined')

        task = serializer.save()

        for prop in task_type.task_type_property.all().exclude(slug = None):
            if type(task_info[prop.slug]) == InMemoryUploadedFile or len(task_info[prop.slug].strip()) > 0:
                if prop.value_type==1 :
                    ser = TaskPropertyNumSerializer(data={'task_type_property':TaskTypePropertySerializer(prop).data,\
                                                    'value':task_info[prop.slug]})
                    ser.is_valid()
                    Task_Property_Num.objects.create(
                        value=ser.validated_data['value'],
                        task=task,
                        task_type_property=prop
                    )
                if prop.value_type==2 :
                    ser = TaskPropertyTextSerializer(data={'task_type_property':TaskTypePropertySerializer(prop).data,\
                                                    'value':task_info[prop.slug]})
                    ser.is_valid()
                    Task_Property_Text.objects.create(
                        value=ser.validated_data['value'],
                        task=task,
                        task_type_property=prop
                    )
                if prop.value_type==3 :
                    ser = TaskPropertyDateSerializer(data={'task_type_property':TaskTypePropertySerializer(prop).data,\
                                                    'value':task_info[prop.slug]})
                    ser.is_valid()
                    Task_Property_Date.objects.create(
                        value=ser.validated_data['value'],
                        task=task,
                        task_type_property=prop
                    )
                if prop.value_type==4 :
                    ser = TaskPropertyFileSerializer(data={'task_type_property':TaskTypePropertySerializer(prop).data,\
                                                    'value':task_info[prop.slug],\
                                                    'filename': task_info[prop.slug].name})
                    ser.is_valid()
                    Task_Property_File.objects.create(
                        value=ser.validated_data['value'],
                        task=task,
                        task_type_property=prop,
                        filename=task_info[prop.slug].name
                    )
                if prop.value_type==5 :
                    ser = TaskPropertyBoolSerializer(data={'task_type_property':TaskTypePropertySerializer(prop).data,\
                                                    'value':task_info[prop.slug]})
                    ser.is_valid()
                    Task_Property_Bool.objects.create(
                        value=ser.validated_data['value'],
                        task=task,
                        task_type_property=prop
                    )

        for v in task_type.verifications.all():
            task_verification_log=Task_Verification_Log.objects.create(
                verification=v,
                task=task
            )
            if v.verification_type == 1:
                task_verification_log.verifier=request.user.employee.organization_group.manager
                if v.verify_by_locumtenens:
                    task_verification_log.verifier_locumtenens=request.user.employee.organization_group.locumtenens
            
            elif v.verification_type == 2:
                organization_group=Organization_Group.objects.filter(group_parent=None).first()
                if organization_group and organization_group.manager:
                    task_verification_log.verifier=organization_group.manager
                    if v.verify_by_locumtenens and organization_group.locumtenens:
                        task_verification_log.verifier_locumtenens=organization_group.locumtenens
                
            elif v.verification_type == 3:
                task_verification_log.verifier=v.verification_user

            if task_verification_log.verifier == task.creator:
                task_verification_log.verified = True
                task_verification_log.last_verifier = task.creator

            
            task_verification_log.save()
        
        for auto_req in task_type.auto_requests.all():
            _request = Task_Assign_Request.objects.create(
                task = task,
                user = auto_req.request_target
            )
            if (task_type.needs_verfication):
                if task.task_verifications.all().exclude(verified=True).count() == 0:
                    _request.need_verification=False
                else:
                    _request.need_verification=True
            else:
                _request.need_verification=False
            _request.save()

            if task_type.froce_assign_request and not _request.need_verification :
                _request.notification_status = 2
                _request.status = 1
                
                _request.save()
                task.assign_status = 4
                task.user_assignee = auto_req.request_target
                task.save()
                start_notif = Notification.objects.create(
                    title='شروع کار '+ task.name,
                    user=task.user_assignee,
                    displaytime=task.startdate + datetime.timedelta(days=1),
                    messages="این کار بایستی در تاریخ " + task.PersianStartDate + " شروع می شد.",
                    link=reverse("api_task:kanban_tasks")
                )
                task.startdate_notification = start_notif
                task.save()

                end_notif = Notification.objects.create(
                    title='اتمام کار '+ task.name,
                    user=task.user_assignee,
                    displaytime=task.enddate + datetime.timedelta(days=1),
                    messages="این کار بایستی در تاریخ " + task.PersianStartDate + " تمام می شد.",
                    link=reverse("api_task:kanban_tasks")
                )
                task.enddate_notification = end_notif
                task.save()
                break

        response = {
            'status': 'success',
            'code': status.HTTP_200_OK,
            'message': 'Request created successfully',
            'data': 'TaskDetailSerializer(task).data'
        }
        return Response(response)


class TaskTypePropertyListView(generics.ListAPIView):
    serializer_class = TaskTypePropertySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        task_type = Task_Type.objects.get(pk = self.kwargs['task_type_id'])
        return Task_Type_Property.objects.filter(task_type = task_type).exclude(slug = None)


class TaskApprovePermission(BasePermission):
    def has_object_permission(self, request, view, obj=None):
        if obj.user_assignee.id in request.user.employee.direct_children_user_id :
            return True
        return False


class TaskApproveView(generics.UpdateAPIView):
    permission_classes = [IsAuthenticated, TaskApprovePermission]
    queryset = Task.objects.all()

    def update(self, request, *args, **kwargs):
        task = self.get_object()
        task.approved = True
        task.save()

        response = {
            'status': 'success',
            'code': status.HTTP_200_OK,
            'message': 'Task Approved successfully',
            'data': TaskDetailSerializer(task).data
        }
        return Response(response)


class TaskCancelPermission(BasePermission):
    def has_object_permission(self, request, view, obj=None):
        if request.user.employee.is_manager:
            if obj.creator == request.user or obj.creator.id in request.user.employee.direct_children_user_id :
                return True
        else:
            if obj.creator == request.user and obj.progress == 0:
                return True
        return False


class TaskCancelView(generics.UpdateAPIView):
    permission_classes = [IsAuthenticated, TaskCancelPermission]
    queryset = Task.objects.all()

    def update(self, request, *args, **kwargs):
        task = self.get_object()
        task.cancelled = True
        task.save()

        response = {
            'status': 'success',
            'code': status.HTTP_200_OK,
            'message': 'Task Cancelled successfully',
            'data': TaskDetailSerializer(task).data
        }
        return Response(response)


class TaskSetExecutorPermission(BasePermission):
    def has_object_permission(self, request, view, obj=None):
        if request.user.employee.is_manager:
            if obj.user_assignee == request.user or obj.user_assignee.id in request.user.employee.direct_children_user_id :
                return True
        else:
            if obj.executor == None and (obj.user_assignee == request.user \
                or obj.user_assignee.id in request.user.employee.parent.direct_children_user_id\
                    or  obj.user_assignee == request.user.employee.parent):
                return True
        return False


class TaskSetExecutorView(generics.UpdateAPIView):
    permission_classes = [IsAuthenticated, TaskSetExecutorPermission]
    queryset = Task.objects.all()
    serializer_class = TaskSetExecutorSerializer

    def update(self, request, *args, **kwargs):
        task = self.get_object()
        serializer = self.get_serializer(data=request.data)

        if serializer.is_valid():
            validated_data = serializer.validated_data
            if request.user.employee.is_manager:
                if validated_data['executor'] != request.user and not validated_data['executor'].id in request.user.employee.direct_children_user_id:
                    return Response(status=status.HTTP_403_FORBIDDEN, data='شما فقط مجاز به تعیین خود یا اعضای تیم خود به عنوان مجری کار هستید.')
            else:
                if validated_data['executor'] != request.user or task.executor != None:
                    return Response(status=status.HTTP_403_FORBIDDEN, data='شما مجاز به تعیین مجری این کار نیستید.')

        updated = super(TaskSetExecutorView, self).update(request, *args, **kwargs)
        new_task = updated.data.serializer.instance

        response = {
            'status': 'success',
            'code': status.HTTP_200_OK,
            'message': 'Task executor changed successfully',
            'data': TaskDetailSerializer(new_task).data
        }
        return Response(response)


class TaskVerificationLogUpdateView(generics.UpdateAPIView):
    permission_classes = [IsAuthenticated]
    queryset = Task_Verification_Log.objects.all()
    serializer_class = TaskVerificationLogUpdateSerializer

    def update(self, request, *args, **kwargs):
        task_verification = self.get_object()
        serializer = self.get_serializer(data=request.data)

        if serializer.is_valid():
            validated_data = serializer.validated_data
            if task_verification.verified == None and (task_verification.verifier == request.user or \
                (task_verification.verifier_locumtenens == request.user and task_verification.verification.verify_by_locumtenens)):
                request.data['last_verifier'] = request.user.id
            else:
                return Response(status=status.HTTP_403_FORBIDDEN, data='شما مجاز به تایید یا رد این درخواست نیستید.')


        updated = super(TaskVerificationLogUpdateView, self).update(request, *args, **kwargs)
        new_task = updated.data.serializer.instance.task

        response = {
            'status': 'success',
            'code': status.HTTP_200_OK,
            'message': 'Task request verified successfully',
            'data': TaskDetailSerializer(new_task).data
        }
        return Response(response)


class TaskAssignRequestUpdateView(generics.UpdateAPIView):
    permission_classes = [IsAuthenticated]
    queryset = Task_Assign_Request.objects.all()
    serializer_class = TaskAssignRequestUpdateSerializer

    def update(self, request, *args, **kwargs):
        assign_request = self.get_object()
        serializer = self.get_serializer(data=request.data)

        if serializer.is_valid():
            validated_data = serializer.validated_data
            if assign_request.status == None and assign_request.user == request.user and validated_data['status'] in [1,2]:
                with transaction.atomic():
                    assign_request.status=validated_data['status']
                    assign_request.status=validated_data['text']
                    assign_request.notification_status=None
                    assign_request.save()
                    if validated_data['status'] == 1:
                        other_task_requests=Task_Assign_Request.objects.filter(task=assign_request.task).exclude(pk=assign_request.id)
                        if task_requests:
                            for r in task_requests:
                                r.notification_status=2
                                r.save()
                        task=assign_request.task
                        task.user_assignee=request.user
                        task.assign_status=4    #request accepted
                        task.save()
                        response = {
                            'status': 'success',
                            'code': status.HTTP_200_OK,
                            'message': 'Task assign accepted successfully',
                            'data': TaskDetailSerializer(new_task).data
                        }
                    else:
                        response = {
                            'status': 'success',
                            'code': status.HTTP_200_OK,
                            'message': 'Task assign rejected successfully',
                            'data': TaskDetailSerializer(new_task).data
                        }
            else:
                return Response(status=status.HTTP_403_FORBIDDEN, data='شما مجاز به پذیرفتن این درخواست نیستید.')

        else:
            response = {
                'status': 'success',
                'code': status.HTTP_400_BAD_REQUEST,
                'message': 'Invalid data',
                'data': TaskDetailSerializer(new_task).data
            }
        return Response(response)


class TaskConfirmPermission(BasePermission):
    def has_object_permission(self, request, view, obj=None):
        if obj.task_type and abj.task_type.is_request:
            if obj.progress == 100 and obj.creator == request.user.id :
                return True
        else:
            if request.user.employee.is_manager and obj.progress == 100 and\
                obj.user_assignee and obj.user_assignee.employee.GetEmployeeParent == request.user.id :
                return True

        return False


class TaskConfirmView(generics.UpdateAPIView):
    permission_classes = [IsAuthenticated, TaskConfirmPermission]
    queryset = Task.objects.all()
    serializer_class = TaskConfirmSerializer

    def update(self, request, *args, **kwargs):
        task = self.get_object()
        serializer = self.get_serializer(data=request.data)
        request.data['confirmed'] = True
        request.data['confirmed_date'] = datetime.datetime.now()

        if serializer.is_valid():
            validated_data = serializer.validated_data
            if validated_data['score'] >= 1 and validated_data['score'] <= 1:
                return Response(status=status.HTTP_403_FORBIDDEN, data='امتیاز وارد شده خارج از محدوده مجاز است.')

            

        updated = super(TaskConfirmView, self).update(request, *args, **kwargs)
        new_task = updated.data.serializer.instance

        response = {
            'status': 'success',
            'code': status.HTTP_200_OK,
            'message': 'Task confirmed successfully',
            'data': TaskDetailSerializer(new_task).data
        }
        return Response(response)


class RequestGroupsListView(generics.ListAPIView):
    serializer_class = OrganizationGroupShortSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        organization_ids = Task_Type_Auto_Request.objects.all().values_list('request_target__employee__organization_group__id')
        return Organization_Group.objects.filter(id__in = organization_ids)


class RequestFullGroupsListView(generics.ListAPIView):
    serializer_class = OrganizationGroupMediumSerializer
    permission_classes = [IsAuthenticated]
    queryset = Organization_Group.objects.all()


class RequestGroupTypesListView(generics.ListAPIView):
    serializer_class = TaskTypeSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        group = Organization_Group.objects.get(pk = self.kwargs['group_id'])
        task_type_ids = Task_Type_Auto_Request.objects.filter(request_target__employee__organization_group__id = group.id).values_list('task_type__id')
        return Task_Type.objects.filter(id__in = task_type_ids)


class RequestTypeCreateView(generics.CreateAPIView):
    serializer_class = RequestTypeCreateSerializer
    permission_classes = [IsAuthenticated]
    queryset = Task_Type.objects.all()

    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data = request.data)
            if serializer.is_valid():
                validated_data = serializer.validated_data
                request_type = Task_Type.objects.create(
                    name=validated_data["name"],
                    creator= request.user,
                    is_request = True,
                    auto_request = True,
                    froce_assign_request = False,
                    needs_verfication = True if len(request.data["verifications"]) > 0 else False,
                    resource_type = None
                )
                auto_requests_data = request.data["auto_requests"]
                for auto_request_data in auto_requests_data:
                    auto_request_ser = TaskTypeAutoRequestCreateSerializer(data=auto_request_data)
                    if auto_request_ser.is_valid():
                        Task_Type_Auto_Request.objects.create(
                            task_type=request_type,
                            request_target_id = auto_request_ser.validated_data["request_target_id"]
                        )

                task_type_props_data = request.data["task_type_property"]
                for task_type_prop_data in task_type_props_data :
                    task_type_prop_ser = TaskTypePropertySerializer(data=task_type_prop_data)
                    if task_type_prop_ser.is_valid():
                        ttp_validated_data = task_type_prop_ser.validated_data
                        Task_Type_Property.objects.create(
                            task_type = request_type,
                            name=ttp_validated_data["name"],
                            value_type=ttp_validated_data["value_type"],
                            order = ttp_validated_data["order"],
                            slug=ttp_validated_data["slug"]
                        )

                verifications_data = request.data["verifications"]
                for verification_data in verifications_data:
                    verification_ser = TaskTypeVerificationSerializer(data=verification_data)
                    if verification_ser.is_valid():
                        ver_validated_data = verification_ser.validated_data
                        Task_Type_Verification.objects.create(
                            task_type = request_type,
                            order = ver_validated_data["order"],
                            verification_type = ver_validated_data["verification_type"],
                            verify_by_locumtenens = ver_validated_data["verify_by_locumtenens"]
                        )

                response = {
                'status': 'success',
                'code': status.HTTP_200_OK,
                'message': 'RequestType created successfully',
                'data': self.get_serializer(request_type).data
                }
                return Response(response)
        except Exception as ex:
            return Response(status=status.HTTP_400_BAD_REQUEST, data=str(ex))


class RequestTypeDestroyPermission(BasePermission):
    def has_object_permission(self, request, view, obj=None):
        if request.user.is_superuser or obj.creator == request.user :
            return True
        return False


class RequestTypeDestroyView(generics.DestroyAPIView):
    permission_classes = [IsAuthenticated, RequestTypeDestroyPermission]
    queryset = Task_Type.objects.all()

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.deleted = True
        instance.save()

        return Response(status=status.HTTP_204_NO_CONTENT)


class TaskExtendPermission(BasePermission):
    def has_permission(self, request, view):
        task = Task.objects.get(pk=request.parser_context['kwargs']['task_id'])
        if task.user_assignee == request.user or task.creator == request.user :
            return True
        return False

    def has_object_permission(self, request, view, obj=None):
        task = Task.objects.get(pk=request.parser_context['kwargs']['task_id'])
        if request.method == "GET":

            if task.creator == request.user or task.user_assignee == request.user or \
                task.creator.id in request.user.employee.all_children_user_id :
                return True
            return False
        elif request.method == 'POST' :
            if task.user_assignee == request.user  :
                return True
            return False
        else:
            if task.creator == request.user :
                return True
            return False


class TaskExtendViewset(viewsets.ModelViewSet):
    serializer_class = TaskExtendSerializer
    permission_classes = [IsAuthenticated & TaskExtendPermission]

    def get_queryset(self):
        return TaskExtend.objects.filter(task_id = self.kwargs['task_id'])

    def create(self, request, *args, **kwargs):
        task = Task.objects.get(pk = self.kwargs['task_id'])
        
        task_extend_ser = self.get_serializer(data = request.data)
        if task_extend_ser.is_valid():
            task_extend_data = task_extend_ser.validated_data
            if task_extend_data['requested_deadline'] > task.enddate :
                TaskExtend.objects.create(task=task, requested_deadline=task_extend_data['requested_deadline'],\
                    description=task_extend_data['description'], previous_deadline=task.enddate)
                response = {
                    'status': 'success',
                    'code': status.HTTP_200_OK,
                    'message': 'Task extend request created successfully',
                    'data': TaskExtendSerializer(task.extends.all(), many=True).data
                }
            
                return Response(response)
            else:
                return Response(status=status.HTTP_400_BAD_REQUEST, data='امکان تمدید به تاریخ قبل از مهلت وجود ندارد.')
        else:
            return Response(status=status.HTTP_400_BAD_REQUEST, data='قالب اطلاعات ارسالی صحیح نیست.')

    def update(self, request, *args, **kwargs):
        task = Task.objects.get(pk = self.kwargs['task_id'])
        
        task_extend_ser = TaskExtendAcceptSerializer(data = request.data)
        if task_extend_ser.is_valid():
            instance = self.get_object()
            task_extend_data = task_extend_ser.validated_data
            if task_extend_data['accepted_deadline'] > task.enddate and instance.accepted_deadline == None and \
                instance.rejected == False:
                
                instance.accepted_deadline = task_extend_data['accepted_deadline']
                instance.save()
                task.enddate = instance.accepted_deadline
                task.save()

                response = {
                    'status': 'success',
                    'code': status.HTTP_200_OK,
                    'message': 'Task extend request accepted successfully',
                    'data': TaskExtendSerializer(task.extends.all(), many=True).data
                }
            
                return Response(response)
            else:
                return Response(status=status.HTTP_400_BAD_REQUEST, data='امکان تمدید به تاریخ قبل از مهلت وجود ندارد.')
        else:
            return Response(status=status.HTTP_400_BAD_REQUEST, data='قالب اطلاعات ارسالی صحیح نیست.')

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.accepted_deadline == None:
            instance.rejected = True
            instance.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class TasksSummaryView(views.APIView):
    serializer_class = TaskSummarySerializer
    permission_classes = [IsAuthenticated]

    def get(self, request):
        
        # Find user based on ?user=<user_id> query param
        if self.request.query_params.get('user',False) and int(self.request.query_params.get('user',None)):
            try:
                if int(self.request.query_params.get('user')) in self.request.user.employee.all_children_user_id:
                    user = User.objects.get(id=int(self.request.query_params.get('user')))
                else:
                    user = self.request.user
            except:
                user = self.request.user
        else:
            user = self.request.user

        if user.employee.is_manager :
            request_pool = Task.objects.filter(task_type__is_request=True,user_assignee=user).exclude(cancelled=True).exclude(confirmed=True)
        else:
            request_pool = Task.objects.filter(task_type__is_request=True,user_assignee=user.employee.parent).exclude(cancelled=True).exclude(confirmed=True)

        requests = Task_Assign_Request.objects.filter(task__creator = user.employee.organization_group.manager).values_list('task__id', flat=True)
        task_filtered =  Task.objects.filter(Q(user_assignee = user,approved=True) |Q(executor = user) |\
            (Q(user_assignee=None,group_assignee=None, creator=user.employee.organization_group.manager)&~Q(id__in=requests))|\
                    Q(approved=False, creator__in=user.employee.direct_children_user_id)|Q(approved=False, creator=user))\
                        .exclude(cancelled=True).exclude(confirmed=True) | request_pool
        
        context={}
        context["CompletedTask"]= task_filtered.filter(progress=100).count()
        context["CurrentTask"]= task_filtered.filter(current=True).count()
        taskExtendList = TaskExtend.objects.values_list('task__id', flat=True)
        context["TaskExtend"]= task_filtered.filter(pk__in=taskExtendList).count()
        context["EducationalTask"]= task_filtered.filter(educational = True).count()
        context["NotEducationalTask"]= task_filtered.filter(educational = False).count()
        context["Canclled"]= task_filtered.filter(cancelled = True).count()
        context["DificultyAverage"]= task_filtered.aggregate(Avg('difficulty'))['difficulty__avg']
        
        return Response(context)


class TasksWithDetailsView(generics.ListAPIView):

    permission_classes = [IsAuthenticated]
    serializer_class = TaskDetailSerializer

    def get_queryset(self):
        # Find user based on ?user=<user_id> query param
        if self.request.query_params.get('user',False) and int(self.request.query_params.get('user',None)):
            try:
                if int(self.request.query_params.get('user')) in self.request.user.employee.all_children_user_id:
                    user = User.objects.get(id=int(self.request.query_params.get('user')))
                else:
                    user = self.request.user
            except:
                user = self.request.user
        else:
            user = self.request.user

        if user.employee.is_manager :
            request_pool = Task.objects.filter(task_type__is_request=True,user_assignee=user).exclude(cancelled=True).exclude(confirmed=True)
        else:
            request_pool = Task.objects.filter(task_type__is_request=True,user_assignee=user.employee.parent).exclude(cancelled=True).exclude(confirmed=True)

        requests = Task_Assign_Request.objects.filter(task__creator = user.employee.organization_group.manager).values_list('task__id', flat=True)
        return Task.objects.filter(Q(user_assignee = user,approved=True) |Q(executor = user) |\
            (Q(user_assignee=None,group_assignee=None, creator=user.employee.organization_group.manager)&~Q(id__in=requests))|\
                    Q(approved=False, creator__in=user.employee.direct_children_user_id)|Q(approved=False, creator=user))\
                        .exclude(cancelled=True).exclude(confirmed=True) | request_pool