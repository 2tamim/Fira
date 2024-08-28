from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path,include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('Tadbir3_app.urls.task', namespace='tasks')),
    path('', include('Tadbir3_app.urls.dashboard', namespace='dashboard')),
    path('', include('Tadbir3_app.urls.task_group', namespace='task_group')),
    path('', include('Tadbir3_app.urls.user', namespace='user')),
    path('', include('Tadbir3_app.urls.time', namespace='time')),
    path('', include('Tadbir3_app.urls.report', namespace='report')),
    path('', include('Tadbir3_app.urls.challenge', namespace='challenge')),
    path('', include('Tadbir3_app.urls.resource', namespace='resource')),
    path('', include('Tadbir3_app.urls.human_resource', namespace='human_resource')),
    path('', include('Tadbir3_app.urls.human_capitals', namespace='human_capitals')),
    path('wallet/', include('Tadbir3_app.urls.wallet', namespace='wallet')),
    path('utils/', include('Tadbir3_app.urls.utils', namespace='utils')),
    path('ckeditor',include('ckeditor_uploader.urls')),
    path('api/user/', include('user.urls', namespace='api_user')),
    path('api/performance/', include('performance.urls', namespace='api_performance')),
    path('api/task/', include('task.urls', namespace='api_task')),
    path('api/tasklog/', include('tasklog.urls', namespace='api_tasklog')),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
