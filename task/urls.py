from django.urls import path, include
from rest_framework_simplejwt import views as jwt_views
from rest_framework.routers import DefaultRouter
from .views import *

app_name = 'api_task'

router = DefaultRouter()

router.register(r'subtask', SubtaskViewset, basename='subtasks')
router.register(r'attachment', TaskAttachmentViewset, basename='task_attachments')
router.register(r'comment', TaskCommentViewset, basename='task_comments')
router.register(r'extend', TaskExtendViewset,base_name='task_extend')

urlpatterns = [
    path('kanban/', KanbanTasksView.as_view(), name='kanban_tasks'),
    path('<int:pk>/', TaskRetrieveUpdateView.as_view(), name='task_detail'),
    path('<int:task_id>/', include(router.urls)),
    path('<int:task_id>/state/', TaskStatesListView.as_view(), name='task_states'),
    path('progress/<int:pk>/', TaskProgressUpdateView.as_view(), name='task_progress_update'),
    path('', TaskCreateView.as_view(), name='task_create'),
    path('request/type/', RequestTypeListView.as_view(), name='request_type_list'),
    path('request/', RequestCreateListView.as_view(), name='request_list'),
    path('request/type/<int:task_type_id>/property/',TaskTypePropertyListView.as_view(), name="request_type_property_list"),
    path('<int:pk>/approve/', TaskApproveView.as_view(), name='task_approve'),
    path('<int:pk>/cancel/', TaskCancelView.as_view(), name='task_cancel'),
    path('<int:pk>/set_executor/', TaskSetExecutorView.as_view(), name='task_set_executor'),
    path('verification/<int:pk>/', TaskVerificationLogUpdateView.as_view(), name='task_verification_log_update'),
    path('request/<int:pk>/', TaskAssignRequestUpdateView.as_view(), name='task_assign_request_update'),
    path('<int:pk>/confirm/', TaskConfirmView.as_view(), name='task_cancel'),
    path('request/group/', RequestGroupsListView.as_view(), name='request_group_list'),
    path('request/group/full/', RequestFullGroupsListView.as_view(), name='request_full_group_list'),
    path('request/group/<int:group_id>/type/', RequestGroupTypesListView.as_view(), name='request_group_type_list'),
    path('request/type/create/', RequestTypeCreateView.as_view(), name='request_type_create'),
    path('request/type/<int:pk>/', RequestTypeDestroyView.as_view(), name='request_type_destroy'),
    path('summary/', TasksSummaryView.as_view(), name='tasks_summary'),
    path('tasks_details/', TasksWithDetailsView.as_view(), name='tasks_with_details'),
]