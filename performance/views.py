from django.shortcuts import get_list_or_404, get_object_or_404
from rest_framework import generics, mixins, viewsets, status, views
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from utils.pagination import NormalPagesPagination

from .serializers import *
# Create your views here.


class FeedbackView(generics.ListCreateAPIView):
    
    pagination_class = NormalPagesPagination
    serializer_class = FeedbackSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Feedback.objects.filter(user = self.request.user).exclude(verified = False, feedback_type__needs_verification = True).order_by('-id')


class FeedbackSeenView(generics.UpdateAPIView):

    serializer_class = FeedbackSeenSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Feedback.objects.filter(user = self.request.user)

    def update(self, request, *args, **kwargs):
        self.object = self.get_object()
        serializer = self.get_serializer(data=request.data)

        if serializer.is_valid() and serializer.data['seen']:
            self.object.seen = True
            self.object.save()
            response = {
                'status': 'success',
                'code': status.HTTP_200_OK,
                'message': 'Feedback updated successfully',
                'data': FeedbackSerializer(self.object).data
            }
            return Response(response)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)