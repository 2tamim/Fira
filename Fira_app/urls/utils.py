from django.urls import path

from ..views.utils import widgets
app_name = 'utils'
urlpatterns = [
    #---------------------------------------------------------------------
    path('file_uploader', widgets.file_uploader,name='file_uploader'),
]