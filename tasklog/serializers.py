from dataclasses import fields
from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from .models import *
from user.serializers import UserSerializer
from task.serializers import KanbanTaskSerializer, TaskTypeStateSerializer


class ReportExtensionSerializer(serializers.ModelSerializer):

    class Meta:
        model = ReportExtension
        fields =[
            'id',
            'chat_summary',
            'target_started',
            'malicious_file_link',
            'succeed',
            'enhancement_score',
            'link_address',
            'link_user_agent',
            'file_type',
            'malware_type',
        ]


class ReportCommentSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = ReportComment
        fields =[
            'user',
            'content'
        ]


class ReportAttachmentSerializer(serializers.ModelSerializer):

    class Meta:
        model = ReportAttachment
        fields = [
            'name',
            'attachment_file',
            'filename'
        ]


class ReportSerializer(serializers.ModelSerializer):
    extension = ReportExtensionSerializer(read_only=True)
    shared_users = UserSerializer(many=True, read_only=True)
    report_attachments = ReportAttachmentSerializer(many=True, read_only=True)
    report_comments = ReportCommentSerializer(many=True, read_only=True)

    class Meta:
        model = Report
        fields =[
            'id',
            'title',
            'content',
            'report_type',
            'confirmed',
            'score',
            'draft',
            'group_shared',
            'month_report',
            'created',
            'updated',
            'shared_users',
            'extension',
            'report_attachments',
            'report_comments',
        ]
        extra_kwargs = {'id': {'read_only': True},
                        'confirmed': {'read_only': True},
                        'score': {'read_only': True},
                        'draft': {'read_only': True},
                        'group_shared': {'read_only': True},
                        'month_report': {'read_only': True},
                        'created': {'read_only': True},
                        'updated': {'read_only': True},
                        'shared_users': {'read_only': True},
                        'extension': {'read_only': True}}


class TasktimeSerializer(serializers.ModelSerializer):
    task = KanbanTaskSerializer(read_only=True)
    user = UserSerializer(read_only=True)
    reports = ReportSerializer(many=True, read_only=True)
    class Meta:
        model = TaskTime
        fields=(
            'id',
            'task',
            'user',
            'start',
            'end',
            'created',
            'teleworking',
            'mission',
            'PersianStartDate',
            'StartTime',
            'EndTime',
            'color',
            'reports',
        )
        extra_kwargs = {'id': {'read_only': True},
                        'PersianStartDate': {'read_only': True},
                        'StartTime': {'read_only': True},
                        'EndTime': {'read_only': True}}


class TaskLogCreateSerializer(serializers.Serializer):
    task_id = serializers.IntegerField()
    report_type = serializers.IntegerField(required=False)
    progress = serializers.IntegerField()
    state_id = serializers.IntegerField(required=False)
    date = serializers.DateField()
    start = serializers.TimeField()
    end = serializers.TimeField()
    teleworking = serializers.BooleanField()
    mission = serializers.BooleanField()
    content = serializers.CharField(required=False)
    report_attachments = serializers.FileField(required=False)
    month_report = serializers.BooleanField()


class TempTimingRecordSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    task = KanbanTaskSerializer(read_only=True)

    class Meta:
        model = TempTimingRecord
        fields = [
            'user',
            'task',
            'start',
            'description',
        ]