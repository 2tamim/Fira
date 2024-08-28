from django.shortcuts import get_list_or_404, get_object_or_404
from rest_framework import generics, mixins, viewsets, status, views
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, BasePermission
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.contrib.auth.password_validation import validate_password as django_validate_password
from django.conf import settings
from utils.pagination import NormalPagesPagination
from django.http import JsonResponse
from khayyam import JalaliDatetime
from .serializers import *
import datetime
# Create your views here.

class UserViewSet(mixins.ListModelMixin,
                  mixins.RetrieveModelMixin,
                  viewsets.GenericViewSet):

    queryset = User.objects.filter(is_active = True, employee__id__gt = 0)
    serializer_class = UserSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['GET'])
    def current_user(self, request):
        user = request.user
        serializer = self.get_serializer(user)
        return Response(serializer.data)


class ChangePasswordView(generics.UpdateAPIView):

    serializer_class = ChangePasswordSerializer
    model = User
    permission_classes = [IsAuthenticated]

    def get_object(self, queryset=None):
        obj = self.request.user
        return obj

    def validate_password(self, value):
        django_validate_password(value)

        # Check if a password is too long
        password_max_length = User._meta.get_field('password').max_length
        if len(value) > password_max_length:
            return Response({"old_password": [_('Password max length is {}'.format(password_max_length))]}, status=status.HTTP_400_BAD_REQUEST)
        if getattr(settings, 'LOCAL_PASSWORD_MIN_LENGTH', 8) and len(value) < getattr(settings, 'LOCAL_PASSWORD_MIN_LENGTH',8):
            return Response({"old_password": [_('Password must be at least {} characters long.'.format(getattr(settings, 'LOCAL_PASSWORD_MIN_LENGTH',8)))]}, status=status.HTTP_400_BAD_REQUEST)
        if getattr(settings, 'LOCAL_PASSWORD_MIN_DIGITS', 1) and sum(c.isdigit() for c in value) < getattr(settings, 'LOCAL_PASSWORD_MIN_DIGITS',1):
            return Response({"old_password": [_('Password must contain at least {} digits.'.format(getattr(settings, 'LOCAL_PASSWORD_MIN_DIGITS',1)))]}, status=status.HTTP_400_BAD_REQUEST)
        if getattr(settings, 'LOCAL_PASSWORD_MIN_UPPER', 1) and sum(c.isupper() for c in value) < getattr(settings, 'LOCAL_PASSWORD_MIN_UPPER', 1):
            return Response({"old_password": [
                _('Password must contain at least {} uppercase characters.'.format(getattr(settings, 'LOCAL_PASSWORD_MIN_UPPER', 1)))
            ]}, status=status.HTTP_400_BAD_REQUEST)
        if getattr(settings, 'LOCAL_PASSWORD_MIN_SPECIAL', 1) and sum(not c.isalnum() for c in value) < getattr(settings, 'LOCAL_PASSWORD_MIN_SPECIAL', 1):
            return Response({"old_password": [
                _('Password must contain at least {} special characters.'.format(getattr(settings, 'LOCAL_PASSWORD_MIN_SPECIAL', 1)))
            ]}, status=status.HTTP_400_BAD_REQUEST)

        return value

    def update(self, request, *args, **kwargs):
        self.object = self.get_object()
        serializer = self.get_serializer(data=request.data)

        if serializer.is_valid():
            if not self.object.check_password(serializer.data.get("old_password")):
                return Response({"old_password": ["Wrong password"]}, status=status.HTTP_400_BAD_REQUEST)
            self.validate_password(serializer.data.get("new_password"))
            self.object.set_password(serializer.data.get("new_password"))
            self.object.save()
            response = {
                'status': 'success',
                'code': status.HTTP_200_OK,
                'message': 'Password updated successfully',
                'data': []
            }

            return Response(response)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ChangeAvatarView(generics.UpdateAPIView):

    serializer_class = ChangeAvatarSerializer
    model = Employee
    permission_classes = [IsAuthenticated]

    def get_object(self, queryset=None):
        obj = self.request.user.employee
        return obj

    def update(self, request, *args, **kwargs):
        self.object = self.get_object()
        serializer = self.get_serializer(data=request.data)

        if serializer.is_valid():
            self.object.avatar = request.FILES.get('avatar')
            self.object.save()
            response = {
                'status': 'success',
                'code': status.HTTP_200_OK,
                'message': 'Avatar updated successfully',
                'data': []
            }
            return Response(response)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class NotificationCountView(views.APIView):
    
    permission_classes = [IsAuthenticated]

    def get(self, request):
        unseen_notifications = Notification.objects.filter(user = request.user,seen= False)
        response = {}
        notification_count = {}
        notification_count['messages'] = unseen_notifications.filter(notif_type = 1).count()
        notification_count['events'] = unseen_notifications.filter(notif_type = 2).count()
        notification_count['mentions'] = unseen_notifications.filter(notif_type = 3).count()

        response['notification_count'] = notification_count

        return Response(response)


class NotificationListView(generics.ListAPIView):

    pagination_class = NormalPagesPagination
    permission_classes = [IsAuthenticated]
    serializer_class = NotificationSerializer

    def get_queryset(self):
        return Notification.objects.filter(user = self.request.user).order_by('-id')


class NotificationUpdateView(generics.UpdateAPIView):

    queryset = Notification.objects.all()
    serializer_class = NotificationUpdateSerializer
    permission_classes = [IsAuthenticated]


    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.user == request.user:
            serializer = self.get_serializer(instance, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)

            return Response(serializer.data)
        return Response(status=status.HTTP_403_FORBIDDEN)


class RegulationView(generics.ListAPIView):
    queryset = Regulation.objects.all()
    serializer_class = RegulationSerializer
    permission_classes = [IsAuthenticated]


class GetServerTime(generics.ListAPIView):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return None

    def list(self, request, *args, **kwargs):
        jalali_date = JalaliDatetime.now()
        formatted_date = jalali_date.strftime("%A %d %B %Y %H:%M:%S")  # Format date in Farsi

        response_data = {
            'server_time': formatted_date,
        }

        return JsonResponse(response_data)


class ChildrenUserListView(generics.ListAPIView):

    permission_classes = [IsAuthenticated]
    serializer_class = ChildUserSerializer

    def get_queryset(self):
        return User.objects.filter(id__in = self.request.user.employee.all_children_user_id, is_active=True).order_by('last_name')


class GlobalNotificationPermission(BasePermission):
    def has_permission(self, request, view):
        if request.user.employee.global_notification_permission:
            return True
        return False


class GlobalNotificationCreateView(generics.CreateAPIView):
    permission_classes = [IsAuthenticated, GlobalNotificationPermission]
    serializer_class = GlobalNotificationSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data = request.data)
        if serializer.is_valid():
            data = serializer.validated_data
            for user in User.objects.filter(is_active=True):
                Notification.objects.create(
                    user=user,
                    title=data['title'],
                    link="/",
                    messages=data['messages'],
                    displaytime=datetime.datetime.now(),
                    notif_type=4
                )

            response = {
                'status': 'success',
                'code': status.HTTP_200_OK,
                'message': 'Notification created successfully'
                }
            return Response(response)
        else:
            return Response(status=status.HTTP_400_BAD_REQUEST, data='اطلاعات وارد شده معتبر نیست.')


class UserSettingPermission(BasePermission):

    def has_object_permission(self, request, view, obj=None):
        if obj.user == request.user :
            return True
        return False


class UserSettingViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = UserSettingsSerializer

    def get_queryset(self):
        if not SystemSetting.objects.filter(user=self.request.user).exists():
            SystemSetting.objects.create(user=self.request.user)
        return SystemSetting.objects.filter(user=self.request.user)
