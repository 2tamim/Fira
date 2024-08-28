from rest_framework import serializers
from ..models import ResourceRelation,ResourceTypeRelation,Resource,ResourceAssignment,ResourceType,ConsumingResource,HardwareResource,ResourceTypeProperty,ResourcePropertyNum,ResourcePropertyText,ResourcePropertyDate,ResourcePropertyFile,ResourcePropertyBool,Organization_Group,Employee,ResourceTaskAssignment
from .task_management_serializer import UserSerializer,TaskSerializer


class ResourceTypePropertySerializer(serializers.ModelSerializer):
    # resource_type=ResourceTypeSerializer(required=True)
    class Meta:
        model = ResourceTypeProperty
        fields = ['id','name','order', 'value_type','isPublic','slug']


class ResourceTypeSerializer(serializers.ModelSerializer):
    resource_type_property = ResourceTypePropertySerializer(many = True)
    class Meta:
        model = ResourceType
        fields = ['id','name','description', 'category','resource_type_property']

class ResourceSerializer(serializers.ModelSerializer):
    creator = UserSerializer(required=True)
    owner = UserSerializer(required=True)
    locumtenens = UserSerializer(required=True)
    resource_type = ResourceTypeSerializer(required=True)
    task = TaskSerializer(required=True)
    class Meta:
        model = Resource
        fields = ['id','name','resource_type', 'creator', 'owner','locumtenens','description','price','task','deleted','created','updated',]

class ResourceMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = Resource
        fields = ['id','name',]

class ResourceAssignmentSerializer(serializers.ModelSerializer):
    #resource = ResourceSerializer(required=True)
    assignee = UserSerializer(required=True)
    class Meta:
        model = ResourceAssignment
        fields = ['id','resource','assignee','description','PersianCreateDate','created','deleted',]

class HardwareResourceSerializer(serializers.ModelSerializer):
    resource=ResourceSerializer(required=True)
    class Meta:
        model = HardwareResource
        fields = ['id','code','serial', 'resource', 'return_status', 'return_date','PersianReturnDate','health','repair','manufacturer','created','updated','LastAssigneeDate',]

class ConsumingResourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConsumingResource
        fields = ['id','resource', 'expiration','PersianExpiration', 'total_amount','consumed_amount','price','created','updated',]

class ResourcePropertyNumSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResourcePropertyNum
        fields = ['id','resource', 'resource_type_property','value',]

class ResourcePropertyTextSerializer(serializers.ModelSerializer):

    class Meta:
        model = ResourcePropertyText
        fields = ['id','resource', 'resource_type_property','value',]

class ResourcePropertyDateSerializer(serializers.ModelSerializer):

    class Meta:
        model = ResourcePropertyDate
        fields = ['id','resource', 'resource_type_property','value','PersianDate',]

class ResourcePropertyFileSerializer(serializers.ModelSerializer):

    class Meta:
        model = ResourcePropertyFile
        fields = ['id','resource', 'resource_type_property','value','filename','get_absolute_url',]

class ResourcePropertyBoolSerializer(serializers.ModelSerializer):

    class Meta:
        model = ResourcePropertyBool
        fields = ['id','resource', 'resource_type_property','value',]
    

class EmployeeSerializer(serializers.ModelSerializer):
    user=UserSerializer(required=True)
    class Meta:
        model = Employee
        fields = ['id','user', 'organization_group',]

class OrganizationGroupSerializer(serializers.ModelSerializer):
    manager=UserSerializer(required=True)
    locumtenens=UserSerializer(required=True)
    employees=EmployeeSerializer(many=True)
    class Meta:
        model = Organization_Group
        fields = ['id','name', 'group_parent','manager','locumtenens','description','created','updated','employees',]


class ResourceTypeRelationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResourceTypeRelation
        fields = ['id','name', 'source_resource_type','order','destinaton_resource_type','multiple','created','updated',]

class ResourceTypeRelationMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResourceTypeRelation
        fields = ['id','name','multiple',]

class ResourceRelationSerializer(serializers.ModelSerializer):
    # relation_type=ResourceTypeRelationSerializer(required=True)
    # source_resource=ResourceSerializer(required=True)
    destinaton_resource=ResourceSerializer(required=True)
    class Meta:
        model = ResourceRelation
        fields = ['id','relation_type', 'source_resource','destinaton_resource','created','updated',]

class ResourceRelationMiniSerializer(serializers.ModelSerializer):

    class Meta:
        model = ResourceRelation
        fields = ['relation_type', 'source_resource','destinaton_resource',]


class ResourceTaskSerializer(serializers.ModelSerializer):
    #resource = ResourceSerializer(required=True)
    task = TaskSerializer(required=True)
    class Meta:
        model = ResourceTaskAssignment
        fields = ['id','resource', 'task','assigner','assignee_notification','created',]
