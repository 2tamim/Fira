from dataclasses import fields
from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from .models import *
from user.serializers import UserSerializer



class EvaluationCriteriaGroupSerializer(serializers.ModelSerializer):

    class Meta:
        model = EvaluationCriteriaGroup
        fields = '__all__'


class EvaluationCriteriaSerializer(serializers.ModelSerializer):
    group = EvaluationCriteriaGroupSerializer()

    class Meta:
        model = EvaluationCriteria
        fields = '__all__'


class EvaluationCriteriaBriefSerializer(serializers.ModelSerializer):
    group = EvaluationCriteriaGroupSerializer()

    class Meta:
        model = EvaluationCriteria
        fields = [
            'name', 
            'description',
            'group',
            'weight',
        ]


class EvaluationNoteSerializer(serializers.ModelSerializer):
    evaluator = UserSerializer()
    evaluatee = UserSerializer()
    criteria = EvaluationCriteriaBriefSerializer()

    class Meta:
        model = EvaluationNote
        fields = '__all__'

class EvaluationLogSerializer(serializers.ModelSerializer):
    evaluator = UserSerializer()
    evaluatee = UserSerializer()
    criteria = EvaluationCriteriaBriefSerializer()

    class Meta:
        model = EvaluationLog
        fields = '__all__'


class FeedbackTypeSerializer(serializers.ModelSerializer):

    class Meta:
        model = FeedbackType
        fields = '__all__'


class FeedbackSerializer(serializers.ModelSerializer):
    feedback_type = FeedbackTypeSerializer()
    user = UserSerializer()
    requester = UserSerializer()
    logs = EvaluationLogSerializer(many=True)

    class Meta:
        model = Feedback
        fields = '__all__'


class FeedbackSeenSerializer(serializers.Serializer):

    seen = serializers.BooleanField()
    class Meta:
        fields = ['seen']