from django.urls import path
from ..views.human_resource import human_resource,degree,skill,certificate,job_experience

app_name = 'human_resource'
urlpatterns = [
    path('human_resource/',human_resource.index,name='human_resource_index'),
    path('human_resource/current_user/summary/',human_resource.UserSummary,name='current_user_summary_page'),
    path('human_resource/user/<int:user_id>/summary/',human_resource.UserSummary,name='specific_user_summary_page'),
    path('human_resource/reports/from/<str:start_date>/to/<str:end_date>/',human_resource.GetUserReportData,name='specific_user_summary_page'),
    path('human_resource/<int:user_id>/<int:year>/<int:month>/addquality/',human_resource.AddEmployeeQuality,name='add_quality'),
    path('human_resource/<int:user_id>/<int:year>/<int:month>/getqualityparameter/',human_resource.GetEmployeeQuality,name='get_quality_parameter'),
    path('human_resource/get_current_month_employee_quality/<int:user_id>/<int:year>/<int:month>/',human_resource.GetCurrentMonthEmployeeQuality,name='get_current_month_employee_quality'),
    #------------------------------------------------------------
    path('human_resource/user/<int:user_id>/degree/add/',degree.Add,name='degree_add'),
    path('human_resource/user/<int:user_id>/degree/list/',degree.ToList,name='degree_list'),
    path('human_resource/user/degree/<int:degree_id>/delete/',degree.Delete,name='degree_delete'),
    path('human_resource/user/degree/<int:degree_id>/detail/',degree.Detail,name='degree_detail'),
    path('human_resource/user/degree/<int:degree_id>/edit/',degree.Edit,name='degree_edit'),
    #------------------------------------------------------------
    path('human_resource/user/<int:user_id>/skill/add/',skill.Add,name='skill_add'),
    path('human_resource/user/<int:user_id>/skill/list/',skill.ToList,name='skill_list'),
    path('human_resource/user/skill/<int:skill_id>/delete/',skill.Delete,name='skill_delete'),
    path('human_resource/user/skill/<int:skill_id>/detail/',skill.Detail,name='skill_detail'),
    path('human_resource/user/skill/<int:skill_id>/edit/',skill.Edit,name='skill_edit'),
    #------------------------------------------------------------
    path('human_resource/user/<int:user_id>/certificate/add/',certificate.Add,name='certificate_add'),
    path('human_resource/user/<int:user_id>/certificate/list/',certificate.ToList,name='certificate_list'),
    path('human_resource/user/certificate/<int:certificate_id>/delete/',certificate.Delete,name='certificate_delete'),
    path('human_resource/user/certificate/<int:certificate_id>/detail/',certificate.Detail,name='certificate_detail'),
    path('human_resource/user/certificate/<int:certificate_id>/edit/',certificate.Edit,name='certificate_edit'),
    #------------------------------------------------------------
    path('human_resource/user/<int:user_id>/job_experience/add/',job_experience.Add,name='job_experience_add'),
    path('human_resource/user/<int:user_id>/job_experience/list/',job_experience.ToList,name='job_experience_list'),
    path('human_resource/user/job_experience/<int:job_experience_id>/delete/',job_experience.Delete,name='job_experience_delete'),
    path('human_resource/user/job_experience/<int:job_experience_id>/detail/',job_experience.Detail,name='job_experience_detail'),
    path('human_resource/user/job_experience/<int:job_experience_id>/edit/',job_experience.Edit,name='job_experience_edit'),

]