from django.urls import path , re_path

from ..views.report import report
app_name = 'report'
urlpatterns = [
    #---------------------------------------------------------------------
    # path('report/<str:report_id>/time/<int:time_id>/<str:kind>/add/',report.add,name='report_add'),
    path('report/list/',report.ReportsList,name='report_list'),
    # re_path('report/list/(?P<u_id[0-9]>)/')
    #path('report/GetReportsInDate/user/<int:user>/<str:date>/',report.GetReportsInDate,name='report_in_date'),
    #path('report/GetPreviousDate/user/<int:user>/<str:date>/',report.GetPreviousDate,name='previous_date'),
    #path('report/GetNextDate/user/<int:user>/<str:date>/',report.GetNextDate,name='next_date'),
    path('report/GetReportDetail/<int:report_id>/',report.GetReportDetail,name='report_detail'),
    path('report/<int:report_id>/delete/',report.DeleteReport,name='report_delete'),
    path('report/<int:report_id>/confirm/score/<int:score>/',report.ConfirmReport,name='report_confirm'),
    #---------------------------------------------------------------------
    path('report/<int:report_id>/attachment/add/',report.AddAttachment,name='attachment_add'),
    path('report/<int:report_id>/attachment/list/',report.AttachmentToList,name='attachment_list'),
    path('report/attachment/delete/<int:id>/',report.DeleteAttachment,name='attachment_delete'),
    #---------------------------------------------------------------------
    path('report/comment/add/',report.AddComment,name='report_comment_add'),
    path('report/<int:report_id>/comment/list/',report.GetCommentList,name='report_comment_list'),
    path('report/<int:report_id>/share/',report.ReportShare,name='report_share'),
    path('report/<int:report_id>/share_group/',report.ReportShareGroup,name='report_share_group'),
    path('report/<int:report_id>/month/',report.MonthReport,name='report_month_report'),
    path('report/month/', report.MonthReportList, name='month_report'),
]