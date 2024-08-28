from django.urls import path, include
from rest_framework_simplejwt import views as jwt_views
from rest_framework.routers import DefaultRouter
from .views import *

app_name = 'api_tasklog'

router = DefaultRouter()

router.register(r'time', TaskTimeViewSet, basename='tasktime')
router.register(r'report', ReportViewSet, basename='report')
router.register(r'timer', TempTimingRecordViewSet,base_name='timer')

urlpatterns = [
    path('', TaskLogCreateView.as_view(), name='task_log_create'),
    path('', include(router.urls)),
    path('task/', LoggableTasksView.as_view(),name='loggable_tasks'),
]