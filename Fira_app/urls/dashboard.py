from django.urls import path

from ..views.dashboard import dashboard

app_name = 'dashboard'
urlpatterns = [
    path('',dashboard.index,name='index'),
    #---------------------------------------------------------------------
    path('dashboard/',dashboard.dashboard,name='dashboard'),
    path('kanban/',dashboard.kanban,name='kanban'),
    path('dashboard/category/add/',dashboard.AddCategory,name='add_category_dashboard'),
    path('dashboard/category/delete/<int:cat_id>/',dashboard.DeleteCategory,name='del_category_dashboard'),
    path('dashboard/category/edit/<int:cat_id>/',dashboard.EditCategory,name='edit_category_dashboard'),
    #----------------------------------------------------------------------
    path('task/<int:task_id>/category/<int:category_id>/add/',dashboard.SetTaskCategory,name='set_task_category'),
    #----------------------------------------------------------------------
    path('dashboard/last_comments/list/',dashboard.GetLastComments,name='get_last_comments'),
    path('dashboard/recent_report/list/',dashboard.GetLastReports,name='get_last_reports'),
    path('dashboard/get_recent_task_progress/list/',dashboard.GetRecentTaskProgress,name='get_recent_task_progress'),
    path('dashboard/get_recent_task_collaburation/<int:user_id>/<int:year>/<int:month>/',dashboard.GetRecentTaskCollaburation,name='get_recent_task_collaburation'),
    path('dashboard/export_user_task_times/',dashboard.ExportUserTaskTimes,name='export_user_task_times'),
    path('dashboard/show_user_quality/',dashboard.ShowEmployeeQuality,name='show_user_quality'),
    path('dashboard/register_user_quality/',dashboard.RegisterEmployeeQuality,name='register_user_quality'),
    path('dashboard/feedback/',dashboard.AddFeedback,name='add_feedback'),
    path('dashboard/feedback/comment/<int:feedback_id>/',dashboard.CommentFeedback,name='comment_feedback'),
    path('dashboard/feedback/verification/<int:feedback_id>/',dashboard.VerifyFeedback,name='verif_feedback'),
    path('dashboard/feedback/reject/<int:feedback_id>/',dashboard.RejectFeedback,name='reject_feedback'),
    path('dashboard/feedback/investigate/<int:feedback_id>/',dashboard.InvestigateFeedback,name='invest_feedback'),
    path('dashboard/feedback/seen/<int:feedback_id>/',dashboard.SeeFeedback,name='see_feedback'),
    path('dashboard/feedback/delete/<int:feedback_id>/',dashboard.DeleteFeedback,name='delete_feedback'),
    path('dashboard/feedback/edit/<int:feedback_id>/',dashboard.EditFeedback,name='edit_feedback'),
    #-----------------------------------Update dashboard elements-----------------------------------
    path('dashboard/kanban-current', dashboard.kanban_current, name = "kanban_current"),
    path('dashboard/kanban-todo', dashboard.kanban_todo, name="kanban_todo"),
    path('dashboard/kanban-doing', dashboard.kanban_doing, name="kanban_doing"),
    path('dashboard/dashboard-calendar/<str:month_diff>', dashboard.dashboard_calendar, name="dashboard_calendar"),
]