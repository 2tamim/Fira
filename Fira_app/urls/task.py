from django.urls import path
from ..views.task import task,task_attachment
from ..views import notification

app_name = 'tasks'
urlpatterns = [
    path('task/add/',task.Add,name='task_add'),
    path('task/list/',task.List,name='task_list'),
    path('task/edit/<int:id>/',task.Edit,name='task_edit'),
    path('task/sibling/<int:id>/',task.GetSiblingTasks,name='task_sibling'),
    path('task/<int:task_id>/progress/<int:amount>/',task.TaskProgresschange,name='task_progress_change'),
    path('task/<int:task_id>/progress/<int:amount>/<str:explicit>/',task.TaskProgresschange,name='task_progress_explicit_change'),
    path('task/get_user_assignee_task/',task.GetUserAssigneeTask,name='get_user_assignee_task'),
    path('task/<int:task_id>/confirm/<int:score>/',task.TaskConfirm,name='task_confirm'),
    #---------------------------------------------------------------------
    path('task/task_type_property/<int:task_type_id>/',task.GetTaskTypeProperty,name='task_type_property_list'),
    path('task/task_type_property_with_value/<int:task_id>/',task.GetTaskTypePropertyWithValue,name='task_type_property_list_with_value'),
    #---------------------------------------------------------------------
    path('task/attachment/add/<int:id>/',task_attachment.add,name='task_attachment_add'),
    path('task/attachment/list/<int:id>/',task_attachment.tolist,name='task_attachment_list'),
    path('task/attachment/delete/<int:id>/',task_attachment.delete,name='task_attachment_delete'),
    path('task/attachment/social_list/<int:id>/',task_attachment.socialtolist,name='social_task_attachment_list'),
    #---------------------------------------------------------------------
    path('notification_number/',notification.GetNotificationNumber,name='notification_number'),
    path('notification_messages/',notification.GetNotificationMessages,name='notification_messages'),
    path('notification/accept/<int:id>/',notification.AcceptNotification,name='accept_notification'),
    #---------------------------------------------------------------------
    path('task/<int:task_id>/resource/<int:resource_id>/add/',task.AddResourceToTask,name='add_resource_to_task'),
    path('task/<int:task_id>/resource/<int:resource_id>/delete/',task.DeleteResourceFromTask,name='delete_resource_from_task'),
    path('task/<int:task_id>/resources/',task.GetResourcesOfTask,name='get_resources_of_task'),
    #---------------------------------------------------------------------
    path('task/<int:task_id>/detail/' , task.GetTaskDetail , name ='get_task_detail'),
    path('task/<int:task_id>/attachment/' , task.GetTaskAttachment , name ='get_task_attachment'),
    path('task/<int:task_id>/profile/' , task.TaskProfileShow , name ='task_profile'),
    path('task/<int:task_id>/gantt/', task.GanttChartPage, name='task_gantt_chart'),
    path('task/<int:task_id>/profile/<int:year>/<int:month>/' , task.TaskProfileUserStatistics , name ='task_profile_user_statistics'),
    path('task/<int:task_id>/last_result/' , task.TaskLastResult , name ='task_last_result'),
    path('task/<int:task_id>/add_comment/',task.AddComment,name='task_add_comment'),
    path('task/<int:task_id>/comment_list/',task.GetCommentList,name='task_comment_list'),
    path('task/<int:task_comment_id>/comment_reply/',task.GetCommentReply,name='task_comment_reply'),
    #---------------------------------------------------------------------
    path('task_type/<int:task_type_id>/get_task_type_auto_request_users/',task.GetTaskTypeAutoRequestUsers,name='get_task_type_auto_request_users'),
    path('task/<int:task_id>/add_user_note/',task.AddUserNote,name='task_user_note'),
    path('task/requests/',task.ListRequests, name='request_list'),
    path('task/requests/<int:task_id>/',task.GetRequestDetail, name='request_detail'),
    path('task/request_accept/<int:task_id>/',task.AcceptTaskRequest,name='accept_task_assign_request'),
    path('task/request_reject/<int:task_id>/',task.RejectTaskRequest,name='reject_task_assign_request'),
    path('task/accept_verification/<int:task_id>/',task.AcceptVerification,name='accept_verification'),
    path('task/reject_verification/<int:task_id>/',task.RejectVerification,name='reject_verification'),
    path('request_number/',notification.GetRequestNumber,name='request_number'),
    #----------------------------------------------------------------------
    path('task/<int:task_id>/copy/' , task.TaskCopy , name ='task_copy'),
    path('task/<int:task_id>/copy_children/' , task.TaskCopyChildren , name ='task_copy_children'),
    #----------------------------------------------------------------------
    path('task/start/<int:task_id>/', task.start, name ='start'),
    path('task/<int:task_id>/panel/' , task.task_detail_panel , name ='task_detail_panel'),
    path('request/', task.request, name='request_page'),

]
