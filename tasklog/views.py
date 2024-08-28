from django.shortcuts import get_list_or_404, get_object_or_404
from django.db.models import Q
from django.urls import reverse
from rest_framework import generics, mixins, viewsets, status, views
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, BasePermission
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.renderers import JSONRenderer
from utils.pagination import NormalPagesPagination,LargePagesPagination
import datetime

from .serializers import *
from user.models import Notification, User
# Create your views here.

class TaskLogCreateView(generics.CreateAPIView):
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = TaskLogCreateSerializer(data=request.data)

        if serializer.is_valid():
            data = serializer.validated_data
            files = request.FILES.getlist('report_attachments')

            if ('content' in data.keys() and len(data['content'])) > 0 :
                return Response(data="امکان ثبت گزارش بدون محتوی وجود ندارد.", status=status.HTTP_400_BAD_REQUEST)

            if data['start'] >= data['end']:
                return Response(data="زمان پایان باید پس از زمان شروع باشد", status=status.HTTP_400_BAD_REQUEST)

            start = datetime.datetime.combine(data['date'],data['start'])
            end = datetime.datetime.combine(data['date'],data['end'])

            _user = request.user
            # this query is used for return conflicted times if exist.
            task_time=TaskTime.objects.filter(Q(start__lte = start,end__gte = end,user =_user )\
                |Q(start__lte = start,end__gt = start,user =_user )\
                    |Q(start__lt = end,end__gte = end,user =_user )\
                        |Q(start__gte = start,end__lte = end,user =_user)\
                            |Q(start__lte = start,end__gte = end,user =_user )\
                                |Q(start__lte = start,end__gt = start,user =_user )\
                                    |Q(start__lt = end,end__gte = end,user =_user )\
                                        |Q(start__gte = start,end__lte = end,user =_user))

            if task_time:
                return Response(data="زمان وارد شده با زمان های  قبل تداخل دارد", status=status.HTTP_400_BAD_REQUEST)
            if (end - start).total_seconds() < 600:
                return Response(data="زمان وارد شده حداقل باید 10 دقیقه باشد", status=status.HTTP_400_BAD_REQUEST)
            if (datetime.datetime.now() - end).total_seconds() < 0:
                return Response(data="امکان ثبت گزارش برای آینده وجود ندارد", status=status.HTTP_400_BAD_REQUEST)

            if SystemPublicSetting.objects.first() and \
                SystemPublicSetting.objects.first().writing_reports_limit_days > 0 and (not data['teleworking'] ) and \
                    (datetime.datetime.now() - end).total_seconds() > (SystemPublicSetting.objects.first().writing_reports_limit_days * 24 + 5) * 3600:
                return Response(data="فرصت ثبت کارکرد برای زمان مد نظر شما تمام شده است", status=status.HTTP_400_BAD_REQUEST)

            if SystemPublicSetting.objects.first() and \
                SystemPublicSetting.objects.first().writing_telework_reports_limit_days > 0 and data['teleworking']:
                try:
                    url = "http://vorud.medad-art.ir//from-date-information"
                    p_id = request.user.employee.personelnumber
                    _date = end + datetime.timedelta(days=1)
                    _date_str = str(_date.strftime(format="%Y/%m/%d"))
                    payload = {'token': 'NDI5M2VjMDgxNGRmYjlhMDMwNGJmODI5NmIwZTMzYzEwMzM2YzE3NTp7Il9hdXRoX3VzZXJfaWQiOiIzIiwiX2F1dGhfdXNlcl9iYWNrZW5kIjoiZ', 'i_date': _date_str, 'p_id': p_id}

                    response = requests.request("POST", url, data = payload)
                    response_time = datetime.datetime.strptime(response.text[:19], '%Y-%m-%d %H:%M:%S')
                    if (datetime.datetime.now() - response_time).total_seconds() > (SystemPublicSetting.objects.first().writing_telework_reports_limit_days * 24 + 5) * 3600:
                        return Response(data="فرصت ثبت کارکرد برای زمان مد نظر شما تمام شده است", status=status.HTTP_400_BAD_REQUEST)
                except:
                    pass
            
            task=Task.objects.get(pk=data['task_id'])
            if task.cancelled:
                return Response(data="ثبت کارکرد برای کارهای کنسل شده امکان پذیر نیست.", status=status.HTTP_400_BAD_REQUEST)
            if not task.current and task.enddate < data['date'] :
                return Response(data="ثبت کارکرد پس از تاریخ اتمام کار امکان پذیر نیست.", status=status.HTTP_400_BAD_REQUEST)


            task_time = TaskTime.objects.create(
                task=task,
                user=_user,
                start = start,
                end = end,
                mission = data['mission'],
                teleworking = data['teleworking']
            )

            task.SetProgressValue(data['progress'])

            if ('content' in data.keys() and len(data['content'])) > 0 or len(files) > 0 :
                if data['report_type'] < 1 or data['report_type'] > 6 :
                    return Response(data="نوع گزارش مشخص شده معتبر نیست.", status=status.HTTP_400_BAD_REQUEST)
                report = Report.objects.create(
                    report_type = data['report_type'],
                    content = data['content'],
                    task_time = task_time,
                    draft=False,
                    month_report = data['month_report'],
                    title = ''
                )

                for _file in files:
                    ReportAttachment.objects.create(
                        name=_file.name, 
                        report=report, 
                        attachment_file=_file, 
                        filename=_file.name
                    )

                if request.user.employee.parent :
                    notification = Notification.objects.create(
                        title="گزارش تائید نشده",
                        user=request.user.employee.parent,
                        displaytime=report.created + datetime.timedelta(days=2),
                        messages=report.task_time.user.first_name+" "+report.task_time.user.last_name +" در تاریخ "+ task_time.PersianEndDate + " گزارش تائید نشده دارد. ",
                        link="/report/list/?r_id=" +str(report.id) 
                    )
                    report.confirmed_notification=notification
                    report.save()

            response = {
                'status': 'success',
                'code': status.HTTP_200_OK,
                'message': 'TaskLog created successfully',
                'data': TasktimeSerializer(task_time).data
            }
            return Response(response)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class TaskTimePermission(BasePermission):
    def has_permission(self, request, view):
        if request.method == "POST":
            return False
        if request.query_params.get('user',False) and int(request.query_params.get('user',0)):
            user = User.objects.get(id=int(request.query_params.get('user')))
            if request.user.id in user.employee.parents or  request.user.id == user.id:
                return True
            return False
        return True

    def has_object_permission(self, request, view, obj=None):
        if request.method == "GET":
            if obj.user == request.user or request.user.id in obj.user.employee.parents:
                return True
            return False
        elif request.method == "PUT" or request.method == "DELETE":
            if obj.user == request.user:
                return True
            return False
        elif obj.user == request.user:
            return True
        return False


class TaskTimeViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated,TaskTimePermission]
    serializer_class = TasktimeSerializer
    pagination_class = LargePagesPagination

    def get_queryset(self):
        # Find user based on ?user=<user_id> query param
        if self.request.query_params.get('user',False) and int(self.request.query_params.get('user',0)):
            user = User.objects.get(id=int(self.request.query_params.get('user')))
        else:
            user = self.request.user

        queryset = TaskTime.objects.filter(user=user).order_by('-start')

        try:
            if self.request.query_params.get('date',False) \
                and datetime.datetime.strptime(self.request.query_params.get('date',None), '%Y-%m-%d'):
                date = datetime.datetime.strptime(self.request.query_params.get('date',None), '%Y-%m-%d')
                queryset = queryset.filter(start__gte=date, end__lte=date+datetime.timedelta(days=1))
        except:
            pass

        return queryset

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)


    def update(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        instance = self.get_object()

        if serializer.is_valid():
            data = serializer.validated_data

            if 'start' in data.keys():
                start = data['start']
            else :
                start = instance.start
            if 'end' in data.keys():
                end = data['end']
            else:
                end = instance.end


            if start >= end:
                return Response(data="زمان پایان باید پس از زمان شروع باشد", status=status.HTTP_400_BAD_REQUEST)

            

            _user = request.user
            # this query is used for return conflicted times if exist.
            task_time=TaskTime.objects.filter(Q(start__lte = start,end__gte = end,user =_user )\
                |Q(start__lte = start,end__gt = start,user =_user )\
                    |Q(start__lt = end,end__gte = end,user =_user )\
                        |Q(start__gte = start,end__lte = end,user =_user)\
                            |Q(start__lte = start,end__gte = end,user =_user )\
                                |Q(start__lte = start,end__gt = start,user =_user )\
                                    |Q(start__lt = end,end__gte = end,user =_user )\
                                        |Q(start__gte = start,end__lte = end,user =_user))\
                                            .exclude(id=instance.id)

            if task_time:
                return Response(data="زمان وارد شده با زمان های  قبل تداخل دارد", status=status.HTTP_400_BAD_REQUEST)
            if (end - start).total_seconds() < 600:
                return Response(data="زمان وارد شده حداقل باید 10 دقیقه باشد", status=status.HTTP_400_BAD_REQUEST)
            if (datetime.datetime.now() - end).total_seconds() < 0:
                return Response(data="امکان ویرایش کارکرد برای آینده وجود ندارد", status=status.HTTP_400_BAD_REQUEST)

            if SystemPublicSetting.objects.first() and \
                SystemPublicSetting.objects.first().writing_reports_limit_days > 0 and (not data['teleworking'] ) and \
                    (datetime.datetime.now() - end).total_seconds() > (SystemPublicSetting.objects.first().writing_reports_limit_days * 24 + 5) * 3600:
                return Response(data="فرصت ویرایش کارکرد برای زمان مد نظر شما تمام شده است", status=status.HTTP_400_BAD_REQUEST)

            if SystemPublicSetting.objects.first() and \
                SystemPublicSetting.objects.first().writing_telework_reports_limit_days > 0 and data['teleworking']:
                try:
                    url = "http://vorud.medad-art.ir//from-date-information"
                    p_id = request.user.employee.personelnumber
                    _date = end + datetime.timedelta(days=1)
                    _date_str = str(_date.strftime(format="%Y/%m/%d"))
                    payload = {'token': 'NDI5M2VjMDgxNGRmYjlhMDMwNGJmODI5NmIwZTMzYzEwMzM2YzE3NTp7Il9hdXRoX3VzZXJfaWQiOiIzIiwiX2F1dGhfdXNlcl9iYWNrZW5kIjoiZ', 'i_date': _date_str, 'p_id': p_id}

                    response = requests.request("POST", url, data = payload)
                    response_time = datetime.datetime.strptime(response.text[:19], '%Y-%m-%d %H:%M:%S')
                    if (datetime.datetime.now() - response_time).total_seconds() > (SystemPublicSetting.objects.first().writing_telework_reports_limit_days * 24 + 5) * 3600:
                        return Response(data="فرصت ویرایش کارکرد برای زمان مد نظر شما تمام شده است", status=status.HTTP_400_BAD_REQUEST)
                except:
                    pass
            
            task=Task.objects.get(pk=data['task_id'])
            if task.cancelled:
                return Response(data="ویرایش کارکرد برای کارهای کنسل شده امکان پذیر نیست.", status=status.HTTP_400_BAD_REQUEST)
            if not task.current and task.enddate < data['date'] :
                return Response(data="ویرایش کارکرد پس از تاریخ اتمام کار امکان پذیر نیست.", status=status.HTTP_400_BAD_REQUEST)

            updated = super(TaskTimeViewSet, self).update(request, *args, **kwargs)
            new_task_time = updated.data.serializer.instance
            response = {
                'status': 'success',
                'code': status.HTTP_200_OK,
                'message': 'Task time updated successfully',
                'data': self.get_serializer(new_task_time).data
            }
            return Response(response)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoggableTasksView(generics.ListAPIView):

    permission_classes = [IsAuthenticated]
    serializer_class = KanbanTaskSerializer

    def get_queryset(self):
        
        user = self.request.user

        return Task.objects.filter(Q(user_assignee = user,approved=True) |Q(executor = user))\
                .exclude(cancelled=True).exclude(confirmed=True).exclude(progress=0).exclude(progress=100)


class ReportPermission(BasePermission):
    def has_permission(self, request, view):
        if request.method == "POST":
            return False
        return True

    def has_object_permission(self, request, view, obj=None):
        if request.method == "GET":
            if obj.task_time.user == request.user or request.user.id in obj.task_time.user.employee.parents:
                return True
            return False
        elif request.method == "PUT" or request.method == "DELETE":
            if obj.task_time.user == request.user:
                return True
            return False
        elif obj.task_time.user == request.user:
            return True
        return False


class ReportViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated,ReportPermission]
    serializer_class = ReportSerializer
    pagination_class = LargePagesPagination

    def get_queryset(self):

        queryset = Report.objects.filter(task_time__user=self.request.user).order_by('-task_time__start')

        return queryset


class TempTimingRecordPermission(BasePermission):

    def has_object_permission(self, request, view, obj=None):
        if obj.user == request.user:
            return True
        return False


class TempTimingRecordViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated,TempTimingRecordPermission]
    serializer_class = TempTimingRecordSerializer

    def get_queryset(self):

        queryset = TempTimingRecord.objects.filter(user=self.request.user)

        return queryset

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)


    def update(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        instance = self.get_object()

        if serializer.is_valid():
            data = serializer.validated_data


    def create(self, request, *args, **kwargs):
        request.data['user_id'] = request.user.id
        request.data['start'] = datetime.datetime.now()
        serializer = self.get_serializer(data=request.data)

        if 'task_id' in request.data.keys() and request.data['task_id'] > 0 :
            task = Task.objects.get(id=request.data['task_id'])
            if task.user_assignee != request.user or task.progress < 1 or task.progress > 99 or task.cancelled:
                return Response(status=status.HTTP_400_BAD_REQUEST, data='شما مجاز به ثبت کارکرد برای این کار نیستید.')

            temp_record = TempTimingRecord.objects.create(
                start=datetime.datetime.now(),
                user=request.user,
                task=task)
            response = {
                'status': 'success',
                'code': status.HTTP_200_OK,
                'message': 'Task timer created successfully',
                'data': TempTimingRecordSerializer(temp_record).data
            }
            return Response(response)
        else:
            return Response(status=status.HTTP_400_BAD_REQUEST, data='اطلاعات وارد شده معتبر نیست.')
