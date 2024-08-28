from rest_framework import serializers
from ..models import Degree,JobExperience

class DegreeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Degree
        fields = ['id','user','level', 'university','field','orientation','PersianFromDate','PersianToDate','description','created','updated',]


class JobExperienceSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobExperience
        fields = ['id','user','organization', 'job_title','PersianFromDate','PersianToDate','description','created','updated',]