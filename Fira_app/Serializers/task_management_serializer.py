from django.db import models,transaction
from rest_framework import serializers
from ..models import Task_Verification_Log,Task_Type_Auto_Request,Task_Group, Task_Group_Member, User, Employee, Task_Assign_Request,TaskTime, Task,Task_Type_Property, Task_Level,Task_Type, Task_Property_Bool,Task_Property_Num, Task_Property_Text, Task_Property_Date, Task_Property_File, TaskComment

class UserOtherInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Employee
        fields = ['avatar', ]


class UserSerializer(serializers.ModelSerializer):
    employee = UserOtherInfoSerializer(required=True)

    class Meta:
        model = User
        fields = ['id', 'first_name', 'last_name', 'is_active', 'employee']


class Task_Group_MemberSerializer(serializers.ModelSerializer):
    user = UserSerializer(required=True)

    class Meta:
        model = Task_Group_Member
        fields = ['user', 'group', ]


class Task_GroupSerializer(serializers.ModelSerializer):
    head = UserSerializer(required=True)
    creator = UserSerializer(required=True)

    class Meta:
        model = Task_Group
        fields = ['name', 'creator', 'head', 'cancelled',
                  'autocancel', 'public', 'created', 'updated', ]

class Task_LevelSerializer(serializers.ModelSerializer):

    class Meta:
        model = Task_Level
        fields = ['id', 'name', 'index', 'description', 'created','updated',]


class TaskSerializer(serializers.ModelSerializer):
    user_assignee = UserSerializer(required=True)
    creator = UserSerializer(required=True)
    group_assignee = Task_GroupSerializer(required=True)

    class Meta:
        model = Task
        fields = ['id','name', 'description', 'task_parent', 'prerequisite_type', 'task_level', 'task_type', 'creator', 'task_group', 'user_assignee', 'group_assignee', 'assign_status', 'budget', 'progress',
                  'progress_autocomplete', 'task_portion_in_parent', 'score', 'cancelled', 'confirmed', 'task_priority', 'startdate', 'enddate', 'created', 'updated', ]


class Task_Assign_RequestSerializer(serializers.ModelSerializer):
    user = UserSerializer(required=True)
    task = TaskSerializer(required=True)

    class Meta:
        model = Task_Assign_Request
        fields = ['id','task', 'user', 'text', 'status', 'notification_status',  ]


class Task_Type_PropertySerializer(serializers.ModelSerializer):
    class Meta:
        model = Task_Type_Property
        fields = ['id','task_type', 'name', 'description', 'value_type', 'order', 'deleted','created','updated',]

class Task_Property_NumSerializer(serializers.ModelSerializer):
    task=TaskSerializer(required=True)
    task_type_property = Task_Type_PropertySerializer(required=True)
    class Meta:
        model = Task_Property_Num
        fields = ['id','task', 'task_type_property', 'value', 'deleted','created','updated',]

class Task_Property_TextSerializer(serializers.ModelSerializer):
    task=TaskSerializer(required=True)
    task_type_property = Task_Type_PropertySerializer(required=True)
    class Meta:
        model = Task_Property_Text
        fields = ['id','task', 'task_type_property', 'value', 'deleted','created','updated',]

class Task_Property_BoolSerializer(serializers.ModelSerializer):
    task=TaskSerializer(required=True)
    task_type_property = Task_Type_PropertySerializer(required=True)
    class Meta:
        model = Task_Property_Bool
        fields = ['id','task', 'task_type_property', 'value', 'deleted','created','updated',]

class Task_Property_DateSerializer(serializers.ModelSerializer):
    task=TaskSerializer(required=True)
    task_type_property = Task_Type_PropertySerializer(required=True)
    class Meta:
        model = Task_Property_Date
        fields = ['id','task', 'task_type_property', 'value','PersianDate', 'deleted','created','updated',]

class Task_Property_FileSerializer(serializers.ModelSerializer):
    task=TaskSerializer(required=True)
    task_type_property = Task_Type_PropertySerializer(required=True)
    class Meta:
        model = Task_Property_File
        fields = ['id','task', 'task_type_property', 'value', 'filename', 'deleted','created','updated','get_absolute_url',]


class Task_TypeSerializer(serializers.ModelSerializer):

    class Meta:
        model = Task_Type
        fields = ['id','name', 'creator', 'public', 'deleted', 'description','created','updated','auto_request', 'froce_assign_request', 'needs_verfication',]


class Task_DetailSerializer(serializers.ModelSerializer):
    user_assignee = UserSerializer(required=True)
    creator = UserSerializer(required=True)
    group_assignee = Task_GroupSerializer(required=True)
    task_level = Task_LevelSerializer(required=True)
    task_type = Task_TypeSerializer(required=True)

    class Meta:
        model = Task
        fields = ['id','name', 'description', 'task_parent', 'prerequisite_type', 'task_level', 'task_type', 'creator', 'task_group', 'user_assignee', 'group_assignee', 'assign_status', 'budget', 'progress',
                  'progress_autocomplete', 'task_portion_in_parent', 'score', 'cancelled', 'confirmed', 'task_priority', 'startdate', 'enddate', 'created', 'updated','PersianStartDate','PersianEndDate', 'PersianCreationDate', 'GetTaskPortionPercentInParent',]

class TaskCommentSerializer(serializers.ModelSerializer):
    user = UserSerializer(required=True)
    task = TaskSerializer(required=True)
    class Meta:
        model = TaskComment
        fields = ['id','content', 'task', 'user','isTaskUserAssignee','PersianCreateDate', 'created','updated',]

class TaskCommentReplySerializer(serializers.ModelSerializer):
    user = UserSerializer(required=True)
    task = TaskSerializer(required=True)
    reply_to = TaskCommentSerializer()
    class Meta:
        model = TaskComment
        fields = ['id','content', 'task', 'user','reply_to','isTaskUserAssignee','PersianCreateDate', 'created','updated',]


class Task_Type_Auto_RequestSerializer(serializers.ModelSerializer):
    request_target = UserSerializer(required=True)
    
    class Meta:
        model = Task_Type_Auto_Request
        fields = ['id','request_target',]


class Task_Verification_LogSerializer(serializers.ModelSerializer):
    last_verifier = UserSerializer(required=True)
    verifier = UserSerializer(required=True)
    class Meta:
        model = Task_Verification_Log
        fields = ['id','verification','task','verified','verifier','verifier_locumtenens','last_verifier','comment','created','updated',]
    

class RecentTaskProgressSerializer(serializers.ModelSerializer):
    progress1=serializers.IntegerField()
    progress2=serializers.IntegerField()
    date1=serializers.DateTimeField()
    date2=serializers.DateTimeField()
    created=serializers.DateTimeField()
    class Meta:
        model = Task
        fields = ['id','name','created','progress1', 'progress2', 'date1', 'date2',]

class TaskRequestSerializer(serializers.ModelSerializer):
    creator = UserSerializer(required=True)
    user_assignee = UserSerializer()
    task_assign_requests = Task_Assign_RequestSerializer(many = True)
    task_verifications = Task_Verification_LogSerializer(many = True)
    task_comments = TaskCommentReplySerializer(many = True)
    class Meta:
        model = Task
        fields = ['id','name', 'description', 'task_level', 'task_type', 'creator', 'user_assignee', 'assign_status', 'task_priority', 'PersianStartDate', 'PersianEndDate', 'current', 'PersianCreationDate', 'task_assign_requests','task_verifications','task_comments',]
