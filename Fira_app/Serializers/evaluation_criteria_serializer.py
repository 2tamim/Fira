from rest_framework import serializers
from ..models import  AutoEvaluationCriteria, AutoEvaluationLog, EvaluationCriteriaGroup, EvaluationCriteria, EvaluationNote, EvaluationLog, EvaluationConsquenseType
from .task_management_serializer import UserSerializer , TaskSerializer

class EvaluationCriteriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = EvaluationCriteria
        fields = ['id','name', 'group', 'weight',]

class EvaluationConsquenseTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = EvaluationConsquenseType
        fields = ['name', 'color_code', 'unimportant',]

class EvaluationNoteSerializer(serializers.ModelSerializer):
    evaluator = UserSerializer(required=True)
    evaluatee = UserSerializer(required=True)
    criteria = EvaluationCriteriaSerializer(required=True)
    consequence_type = EvaluationConsquenseTypeSerializer()
    class Meta:
        model = EvaluationNote
        fields = ['id','note', 'evaluator', 'evaluatee', 'criteria', 'consequence_amount', 'consequence_type', 'month', 'year', 'jcreated', 'jupdated','private','show_to_all',]