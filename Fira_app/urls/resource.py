from django.urls import path

from ..views.resource import resource,internet,report,infrastructure
app_name = 'resource'
urlpatterns = [
    #---------------------------------------------------------------------
    path('resource/add/',resource.add,name='resource_add'),
    path('resource/<int:resource_id>/edit/',resource.add,name='resource_edit'),
    path('resource/list/',resource.ToList,name='resource_list'),
    path('resource/<int:resource_id>/list/',resource.ToList,name='resource_list_with_detail'),
    path('resource/<int:resource_id>/detail/',resource.GetResourceDetails,name='resource_detail'),
    path('resource/<int:resource_id>/delete/',resource.Delete,name='resource_delete'),
    path('resource/<int:resource_id>/logical_delete/',resource.LogicalDelete,name='resource_logical_delete'),
    #---------------------------------------------------------------------
    path('resource/resource_type_property/<int:resource_type>/',resource.GetResourceTypeProperty,name='get_resource_type_property'),
    path('resource/<int:resource_id>/resource_type_property_value/',resource.GetResourceTypePropertyValue,name='get_resource_type_property_value'),
    path('resource/consuming_resource/add/',resource.AddNewConsumingResource,name='consuming_resource_add'),
    path('resource/<int:resource_id>/relation/list/',resource.GetAllRelationsOfResource,name='get_all_relations_Resource'),
    #---------------------------------------------------------------------
    path('resource/<str:resource_id>/resource_type/<int:resource_type_id>/relations/<int:mode>/',resource.GetResourceRelations,name='get_resource_relations'),
    #---------------------------------------------------------------------
    path('resource/internet/',internet.ToList,name='resource_internet'),
    path('resource/internet/data/<int:year>/<int:month>/order/<int:order_id>/',internet.GetInternetData,name='get_internet_data'),
    path('resource/internet/data/user/<int:user_id>/year/<int:year>/',internet.GetInternetUserDataInYear,name='get_internet_user_data_in_year'),
    #---------------------------------------------------------------------
    path('resource/infrastructure/',infrastructure.ToList,name='resource_infrastructure'),
    #---------------------------------------------------------------------
    path('resource/report/',report.index,name='resource_report'),
    path('resource/report/search/',report.GetHardwareResource,name='resource_report_search'),
    path('resource/<str:resource_id>/description/add/',resource.SaveAssigneeDescription,name='save_assignee_desctiption'),
    #---------------------------------------------------------------------
    path('resource/exportsoftwareresources/',resource.ExportSoftwarereSources,name='export_software_resources'),
    path('resource/exporthardwareresources/',resource.ExportHardwareResources,name='export_hardware_resources'),
    path('resource/exportconsumingresources/',resource.ExportConsumingResources,name='export_consuming_resources'),
    #---------------------------------------------------------------------
    path('resource_type/<int:resource_type>/task/list/',resource.GetAllTaskOfResourceType,name='get_all_task_of_resource_type'),
    path('resource/<int:resource_id>/hardware_code/<str:code>/check/',resource.CheckHardwareCodeReplicated,name='check_hardware_code_replicated'),
]