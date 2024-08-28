from django.urls import path

from ..views.human_capitals import human_capitals

app_name = 'human_capitals'
urlpatterns = [
    path('human_capitals/',human_capitals.index,name='index'),
    path('human_capitals/criteria_description/',human_capitals.criteria_description,name='criteria_description'),
    path('human_capitals/get_notes/',human_capitals.get_notes,name='get_notes'),
    path('human_capitals/delete_note/<int:note_id>/',human_capitals.delete_note,name='delete_note'),
    path('human_capitals/upload_excel/', human_capitals.upload_excel,name='upload_excel'),
    path('human_capitals/upload_leave_excel/', human_capitals.upload_leave_excel,name='upload_leave_excel'),
    path('human_capitals/staff_report/', human_capitals.ShowStaffReport,name='staff_report'),
    path('human_capitals/sajjad/', human_capitals.SajjadReports,name='sajjad_report')
    # path('human_capitals_upload/',human_capitals.performance,name='list'),
]