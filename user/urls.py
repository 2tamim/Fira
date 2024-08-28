from django.urls import path, include
from rest_framework_simplejwt import views as jwt_views
from rest_framework.routers import DefaultRouter
from .views import *

app_name = 'api_user'

router = DefaultRouter()

router.register(r'users', UserViewSet, basename='users')
router.register(r'settings', UserSettingViewSet, basename='user_settings')

urlpatterns = [
    path('token/', jwt_views.TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', jwt_views.TokenRefreshView.as_view(), name='token_refresh'),
    path('', include(router.urls)),
    path('password/',ChangePasswordView.as_view(),name="change_password"),
    path('avatar/',ChangeAvatarView.as_view(),name="change_avatar"),
    path('notification/count/', NotificationCountView.as_view(),name="notifications_count"),
    path('notification/', NotificationListView.as_view(),name="notification_list"),
    path('notification/<int:pk>/', NotificationUpdateView.as_view(),name="notification_update"),
    path('regulation/', RegulationView.as_view(),name='regulations'),
    path('get_server_time/', GetServerTime.as_view(), name='get_server_time'),
    path('users/current_user/', UserViewSet.as_view({'get': 'current_user'}), name='current_user'),
    path('children/', ChildrenUserListView.as_view(),name='children_users'),
    path('notification/global/', GlobalNotificationCreateView.as_view(),name="global_notification"),
]