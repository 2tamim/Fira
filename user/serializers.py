from dataclasses import fields
from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from .models import *
from django.templatetags.static import static
from django.conf import settings
import os

class UserSerializer(serializers.ModelSerializer):
    username = serializers.CharField(required=False)
    # personelnumber = serializers.CharField(source='employee.personelnumber', read_only=True)
    # new_personelnumber = serializers.CharField(source='employee.new_personelnumber', read_only=True)
    avatar = serializers.CharField(source='employee.avatar',required=False)

    class Meta:
        model = User
        fields = (
            'id',
            'username',
            'first_name',
            'last_name',
            'email',
            'is_superuser',
            'last_login',
            'avatar',
        )
        extra_kwargs = {'last_login': {'read_only': True}}

    def get_related(self, obj):
        res = super(UserSerializer, self).get_related(obj)

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        if rep['avatar'] is None or rep['avatar'] == '':
            avatar = ""
            avatar_list = [name for name in os.listdir('C:\\kara\\static\\avatar')]
            avatar_count = len(avatar_list)
            avatar_index = instance.id % avatar_count
            rep["avatar"] = static('avatar/'+avatar_list[avatar_index])
        else :
            rep['avatar'] = 'media/' + rep['avatar']

        return rep


class ChildUserSerializer(UserSerializer):
    class Meta(UserSerializer.Meta):
        fields = (
            'id',
            'username',
            'first_name',
            'last_name',
            'email',
            'is_superuser',
            'last_login',
            'avatar',
        )


class ChangePasswordSerializer(serializers.Serializer):

    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)


class ChangeAvatarSerializer(serializers.Serializer):

    avatar = serializers.FileField(required=True)
    class Meta:
        fields = ['avatar']


class NotificationSerializer(serializers.ModelSerializer):

    class Meta:
        model = Notification
        fields = '__all__'


class NotificationUpdateSerializer(serializers.ModelSerializer):

    seen = serializers.BooleanField()
    closed = serializers.BooleanField()

    class Meta:
        model = Notification
        fields = ['seen', 'closed']


class RegulationSerializer(serializers.ModelSerializer):

    class Meta:
        model = Regulation
        fields = '__all__'


class OrganizationGroupShortSerializer(serializers.ModelSerializer):

    class Meta:
        model = Organization_Group
        fields = [
            'id',
            'name',
            'description',
        ]


class OrganizationGroupMediumSerializer(serializers.ModelSerializer):
    manager = UserSerializer()

    class Meta:
        model = Organization_Group
        fields = [
            'id',
            'name',
            'description',
            'manager',
        ]


class GlobalNotificationSerializer(serializers.ModelSerializer):

    class Meta:
        model = Notification
        fields = [
            'title',
            'messages',
        ]


class UserSettingsSerializer(serializers.ModelSerializer):

    class Meta:
        model = SystemSetting
        fields = [
            'id',
            'notification_for_report',
            'notification_for_confirm_report',
            'notification_for_task_times',
            'theme_color',
            'dark_mode',
        ]