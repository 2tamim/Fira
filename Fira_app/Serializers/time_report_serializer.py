from rest_framework import serializers
from ..models import Report,TaskTime,ReportComment , ReportExtension , MonthlyPerformanceReport
from .task_management_serializer import UserSerializer , TaskSerializer

class TaskTimeSerializer(serializers.ModelSerializer):
    task = TaskSerializer(required=True)
    class Meta:
        model = TaskTime
        fields = ['id','task', 'user', 'PersianStartDate', 'PersianEndDate','StartTime','EndTime','teleworking','mission',]

class ReportSerializer(serializers.ModelSerializer):
    task_time = TaskTimeSerializer(required=True)
    class Meta:
        model = Report
        fields = ['id','title', 'content', 'task_time', 'confirmed','score','draft',]

class ReportCommentSerializer(serializers.ModelSerializer):
    user = UserSerializer(required=True)
    report = ReportSerializer(required=True)
    class Meta:
        model = ReportComment
        fields = ['id','content', 'report', 'isReportCreator', 'user','PersianCreateDate','created',]

class ReportExtensionSerializer(serializers.ModelSerializer):
    report = ReportSerializer(required=True)
    class Meta:
        model = ReportExtension
        fields = ['id','report','chat_summary', 'target_started', 'malicious_file_link', 'succeed','enhancement_score', 'link_address', 'link_user_agent', 'file_type', 'malware_type',]

# class MonthlyPerformanceReportSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = MonthlyPerformanceReport
#         fields = ['user','solar_month','solar_year', 'entry_sum', 'presence', 'performance','leave_hourse', 'delay_hourse', 'rush_hourse', 'lowtime', 'overtime', 'holiday_overtime', 'month_days', 'month_holidays',]

