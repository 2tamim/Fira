from django.urls import path

from ..views.task_group import task_group
app_name = 'task_group'
urlpatterns = [
    #---------------------------------------------------------------------
    path('task_group/',task_group.index,name='task_group'),
    path('task_group/add/',task_group.add,name='task_group_add'),
    path('task_group/detail/<int:id>/',task_group.detail,name='task_group_detail'),
    path('task_group/delete/<int:id>/',task_group.delete,name='task_group_delete'),
    path('task_group/edit/<int:id>/',task_group.edit,name='task_group_edit'),
    #---------------------------------------------------------------------
]