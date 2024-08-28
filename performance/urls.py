from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import *

app_name = 'api_performance'


urlpatterns = [
    path('feedback/', FeedbackView.as_view(),name='feedback'),
    path('feedback/<int:pk>/seen/', FeedbackSeenView.as_view(),name="feedback_seen"),
]