from rest_framework import serializers
from ..models import Challenge , ChallengeSolution , ChallengeComment , SolutionComment
from .task_management_serializer import UserSerializer

class SolutionCommentSerializer(serializers.ModelSerializer):
    user = UserSerializer(required=True)
    class Meta:
        model = SolutionComment
        fields = ['id', 'content', 'user',"created", "updated","PersianCreateDate",]

class ChallengeSolutionSerializer(serializers.ModelSerializer):
    user = UserSerializer(required=True)
    solution_comment = SolutionCommentSerializer(many = True)
    class Meta:
        model = ChallengeSolution
        fields = ['id', 'content', 'user', 'confirmed_by_auther',"created", "updated","PersianCreateDate",'AgreeVote','DisAgreeVote',"solution_comment",]

class ChallengeCommentSerializer(serializers.ModelSerializer):
    user = UserSerializer(required=True)
    class Meta:
        model = ChallengeComment
        fields = ['id', 'content', 'user',"created", "updated","PersianCreateDate",]

class ChallengeSerializer(serializers.ModelSerializer):
    user = UserSerializer(required=True)
    challenge_comment = ChallengeCommentSerializer(many = True)
    challenge_solution = ChallengeSolutionSerializer(many = True)
    class Meta:
        model = Challenge
        fields = ['id','title', 'content', 'user', 'public_access','importance','situation',"created", "updated","PersianCreateDate","CommentsNumber", "SolutionsNumber",'SameChallengeNumber',"challenge_comment","challenge_solution",] 


