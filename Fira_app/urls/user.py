from django.urls import path

from ..views.user import user,user_authentication
app_name = 'user'
urlpatterns = [
    #---------------------------------------------------------------------
    path('login/',user_authentication.sitelogin,name='login'),
    path('logout/',user_authentication.logout_view,name='logout'),
    path('user/edit/',user.edit,name='edit_user'),
    #---------------------------------------------------------------------
    path('user/change_image/',user.change_image,name='change_image_user'),
    path('user/delete_image/',user.delete_image,name='delete_image_user'),
    #---------------------------------------------------------------------
    path('user/system_setting/save/',user.SaveSystemSetting,name='save_system_setting'),
    path('user/system_setting/',user.ReadSystemSetting,name='get_system_setting'),
    #---------------------------------------------------------------------
    path('user/system_sessions/',user.ShowSystemSessions,name='get_system_sessions'),
    path('user/regulation/',user.ReadRegulation,name='get_regulation'),
]