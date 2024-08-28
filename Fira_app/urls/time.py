from django.urls import path
from ..views.time import time
app_name = 'time'
urlpatterns = [
    path('task/<int:task_id>/start_task_time/<int:kind>/',time.StartTaskTime,name='start_task_time'),
    path('task/cancel_task_time/',time.CancelTaskTime,name='cancel_task_time'),
    path('task/get_task_time/',time.GetTaskTime,name='get_task_time'),
    path('task/confirm_task_time/',time.ConfirmTaskTime,name='confirm_task_time'),
    #---------------------------------------------------------------------
    path('time&report/add/',time.TimeAndReport,name='time_and_report_add'),
    path('time/<int:time_id>/report/<int:report_id>/edit/',time.TimeAndReport,name='report_edit'),
    path('time/<int:time_id>/report/add/',time.TimeAndReport,name='report_add'),
    path('time/list/',time.TimeList,name='time_list'),
    path('time/SetDesctiption/',time.SetTempTaskTimeDescription,name='set_time_description'),
    path('time/<int:time_id>/<str:kind>/detail/',time.GetTaskTimeDetail,name='time_detail'),
    path('time/edit/',time.EditTaskTimeDetail,name='time_edit'),
    path('time/<int:time_id>/<str:kind>/delete/',time.DeleteTimeWithReports,name='time_delete'),
    #---------------------------------------------------------------------
    path('time/get_week_day/<str:year>/<str:month>/',time.GetMonthDays,name='time_get_week_day'),
    path('time/user/<int:user_id>/get_times_day/<str:year>/<str:month>/',time.GetTimesDays,name='time_get_times_day'),
    path('time/user/<int:user_id>/get_traffics_day/<str:year>/<str:month>/',time.GetTrafficsDays,name='time_get_traffics_day'),
    path('time/get_month_traffics_day/<int:user_id>/<int:year>/<int:month>/',time.GetMonthTrafficsDays,name='time_get_month_traffics_day'),
    path('time/<int:time_id>/reports/',time.GetTimeReports,name='get_reports_of_task_time'),
    path('time/get_times_in_day/<str:year>/<str:month>/<str:day>/',time.GetTimesInDay,name='get_times_in_day'),
    path('time/user/<int:user_id>/get_times_in_day/<str:year>/<str:month>/<str:day>/',time.GetTimesInDay,name='get_times_in_day'),

    #---------------------------------------------------------------------
    path('time/<int:task_id>/panel/' , time.task_time_panel , name ='task_time_panel'),
    path('time/timeline/single/<str:date>' , time.single_date_timeline , name ='single_date_timeline'),
]