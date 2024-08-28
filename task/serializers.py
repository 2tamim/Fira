from dataclasses import fields
from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from .models import *
from user.serializers import UserSerializer, OrganizationGroupShortSerializer\
    , Organization_Group, OrganizationGroupMediumSerializer


class KanbanTaskSerializer(serializers.ModelSerializer):
    creator = UserSerializer()
    user_assignee = UserSerializer()

    class Meta:
        model = Task
        fields = (
            'id',
            'name',
            'creator',
            'user_assignee',
            'assign_status',
            'progress',
            'task_priority',
            'current',
            'approved',
            'tag',
            'wait',
            'deadline_status',
        )


class TaskTypeSerializer(serializers.ModelSerializer):

    class Meta:
        model = Task_Type
        fields = (
            'pk',
            'name',
            'public',
            'is_request',
        )


class TaskAssignRequestSerializer(serializers.ModelSerializer):
    user = UserSerializer()

    class Meta:
        model = Task_Assign_Request
        fields = (
            'user',
            'status',
            'text',
            'need_verification',
        )

    
class TaskTypeStateSerializer(serializers.ModelSerializer):
    possible_previous_states = serializers.SerializerMethodField

    class Meta:
        model = Task_Type_State
        fields = (
            'name',
            'initial',
            'possible_previous_states',
        )

    def get_possible_previous_states(self,obj):
        if obj.possible_previous_states.all().count() :
            return TaskTypeStateSerializer(obj.possible_previous_states.all(),many=True).data
        else:
            return None


class TaskTypePropertySerializer(serializers.ModelSerializer):

    class Meta:
        model = Task_Type_Property
        fields =(
            'name',
            'description',
            'value_type',
            'order',
            'slug',
        )


class TaskPropertyNumSerializer(serializers.ModelSerializer):
    task_type_property = TaskTypePropertySerializer(required=True)

    class Meta:
        model = Task_Property_Num
        fields = ('id',
            'task_type_property',
            'value',
            'deleted',
        )


class TaskPropertyTextSerializer(serializers.ModelSerializer):
    task_type_property = TaskTypePropertySerializer(required=True)

    class Meta:
        model = Task_Property_Text
        fields = ('id',
            'task_type_property',
            'value',
            'deleted',
        )


class TaskPropertyBoolSerializer(serializers.ModelSerializer):
    task_type_property = TaskTypePropertySerializer(required=True)

    class Meta:
        model = Task_Property_Bool
        fields =('id',
            'task_type_property',
            'value',
            'deleted',
        )


class TaskPropertyDateSerializer(serializers.ModelSerializer):
    task_type_property = TaskTypePropertySerializer(required=True)

    class Meta:
        model = Task_Property_Date
        fields = ('id',
            'task_type_property',
            'value',
            'PersianDate',
            'deleted',
        )


class TaskPropertyFileSerializer(serializers.ModelSerializer):
    task_type_property = TaskTypePropertySerializer(required=True)

    class Meta:
        model = Task_Property_File
        fields = ('id',
            'task_type_property',
            'value',
            'filename',
            'deleted',
            'get_absolute_url',
        )


class TaskAttachmentSerializer(serializers.ModelSerializer):
    user = UserSerializer()

    class Meta:
        model = Task_Attachment
        fields = (
            'pk',
            'name',
            'attachment_file',
            'filename',
            'user',
        )


class TaskTypeVerificationSerializer(serializers.ModelSerializer):
    verification_user = UserSerializer(required=False)

    class Meta:
        model = Task_Type_Verification
        fields = (
            'order',
            'verification_type',
            'verify_by_locumtenens',
            'verification_user'
        )


class TaskVerificationLogSerializer(serializers.ModelSerializer):
    verification = TaskTypeVerificationSerializer()
    verifier = UserSerializer()
    verifier_locumtenens = UserSerializer()
    last_verifier = UserSerializer()

    class Meta:
        model = Task_Verification_Log
        fields = (
            'verification',
            'verified',
            'verifier',
            'verifier_locumtenens',
            'last_verifier',
            'comment',
            'updated',
        )


class TaskCommentSerializer(serializers.ModelSerializer):
    user = UserSerializer()

    class Meta:
        model = TaskComment
        fields = (
            'pk',
            'content',
            'user',
            'created',
        )


class SubtaskSerializer(serializers.ModelSerializer):


    class Meta:
        model = Subtask
        fields = (
            'pk',
            'name',
            'done',
            'done_time',
            'order',
        )
        extra_kwargs = {'done_time': {'read_only': True}}


class TaskExtendSerializer(serializers.ModelSerializer):


    class Meta:
        model = TaskExtend
        fields = (
            'pk',
            'previous_deadline',
            'requested_deadline',
            'description',
            'rejected',
            'accepted_deadline',
        )
        extra_kwargs = {'rejected': {'read_only': True},
                        'previous_deadline': {'read_only': True}
                        }


class TaskExtendAcceptSerializer(serializers.ModelSerializer):


    class Meta:
        model = TaskExtend
        fields = (
            'accepted_deadline',
        )


class TaskDetailSerializer(serializers.ModelSerializer):
    task_parent = KanbanTaskSerializer()
    task_type = TaskTypeSerializer()
    creator = UserSerializer()
    user_assignee = UserSerializer()
    state = TaskTypeStateSerializer()
    task_assign_requests = TaskAssignRequestSerializer(many=True)
    task_num_properties = TaskPropertyNumSerializer(many=True)
    task_text_properties = TaskPropertyTextSerializer(many=True)
    task_bool_properties = TaskPropertyBoolSerializer(many=True)
    task_date_properties = TaskPropertyDateSerializer(many=True)
    task_file_properties = TaskPropertyFileSerializer(many=True)
    task_attachments = TaskAttachmentSerializer(many=True)
    task_verifications = TaskVerificationLogSerializer(many=True)
    task_comments = TaskCommentSerializer(many=True)
    subtasks = SubtaskSerializer(many=True)
    executor = UserSerializer()
    extends = TaskExtendSerializer(many=True)

    class Meta:
        model = Task
        fields = (
            'id',
            'name',
            'description',
            'task_parent',
            'task_type',
            'creator',
            'user_assignee',
            'assign_status',
            'progress',
            'task_priority',
            'PersianStartDate',
            'PersianEndDate',
            'startdate',
            'enddate',
            'current',
            'difficulty',
            'approved',
            'educational',
            'state',
            'tag',
            'task_assign_requests',
            'task_num_properties',
            'task_text_properties',
            'task_bool_properties',
            'task_date_properties',
            'task_file_properties',
            'task_attachments',
            'task_verifications',
            'task_comments',
            'subtasks',
            'request_status',
            'executor',
            'PersianCreationDate',
            'wait',
            'deadline_status',
            'extends',
            'task_status'
        )


class ChangeTaskProgressSerializer(serializers.Serializer):

    progress = serializers.IntegerField(required=True)
    class Meta:
        fields = ['progress']


class TaskCreateSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Task
        fields = [
            'name',
            'description',
            'task_parent',
            'task_type',
            'creator',
            'user_assignee',
            'startdate',
            'enddate',
            'current',
            'difficulty',
            'approved',
            'educational',
            'assign_status',
            'task_priority',
        ]


class TaskUpdateSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Task
        fields = [
            'name',
            'description',
            'task_parent',
            'user_assignee',
            'startdate',
            'enddate',
            'current',
            'difficulty',
            'approved',
            'educational',
            'wait',
            'deadline_status',
            'task_priority',
        ]


class TaskSetExecutorSerializer(serializers.ModelSerializer):

    class Meta:
        model = Task
        fields = [
            'executor',
        ]


class TaskVerificationLogUpdateSerializer(serializers.ModelSerializer):

    class Meta:
        model = Task_Verification_Log
        fields = (
            'verified',
            'comment',
            'last_verifier',
        )


class TaskAssignRequestUpdateSerializer(serializers.ModelSerializer):

    class Meta:
        model = Task_Assign_Request
        fields = (
            'status',
            'text',
        )


class TaskConfirmSerializer(serializers.ModelSerializer):

    class Meta:
        model = Task
        fields = [
            'confirmed',
            'confirmed_date',
            'score',
        ]


class TaskTypeAutoRequestCreateSerializer(serializers.Serializer):
    request_target_id = serializers.IntegerField()

    class Meta:
        fields = [
            'request_target_id',
        ]


class RequestTypeCreateSerializer(serializers.ModelSerializer):
    task_type_property = TaskTypePropertySerializer(many=True, required=False)
    auto_requests = TaskTypeAutoRequestCreateSerializer(many=True)
    verifications = TaskTypeVerificationSerializer(many=True, required=False)

    class Meta:
        model = Task_Type
        fields = [
            'name',
            'is_request',
            'task_type_property',
            'auto_requests',
            'verifications',
        ]


class TaskSummarySerializer(serializers.Serializer):
    CompletedTask = serializers.DecimalField(required=False,max_digits=10,decimal_places=0)
    CurrentTask = serializers.DecimalField(required=False,max_digits=10,decimal_places=0)
    TaskExtend = serializers.DecimalField(required=False,max_digits=10,decimal_places=0)
    EducationalTask = serializers.DecimalField(required=False,max_digits=10,decimal_places=0)
    NotEducationalTask = serializers.DecimalField(required=False,max_digits=10,decimal_places=0)
    DificultyAverage = serializers.DecimalField(required=False,max_digits=10,decimal_places=0)
