from __future__ import annotations

from django.contrib.auth import authenticate, login, logout
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.models import Destination, MetricPoint, Route, Source, WebhookDelivery

from .serializers import (
    DestinationSerializer, MetricPointSerializer, RouteSerializer,
    SourceSerializer, WebhookDeliverySerializer,
)


class LoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request: Request) -> Response:
        username = request.data.get('username', '')
        password = request.data.get('password', '')
        if not username or not password:
            return Response({'detail': 'username and password are required.'}, status=status.HTTP_400_BAD_REQUEST)
        user = authenticate(request, username=username, password=password)
        if user is None:
            return Response({'detail': 'Invalid credentials.'}, status=status.HTTP_401_UNAUTHORIZED)
        login(request, user)
        return Response({'id': user.pk, 'username': user.username, 'email': user.email, 'is_staff': user.is_staff})


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        logout(request)
        return Response({'detail': 'Logged out.'})


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        u = request.user
        return Response({'id': u.pk, 'username': u.username, 'email': u.email, 'is_staff': u.is_staff})


class SourceViewSet(viewsets.ModelViewSet):
    queryset = Source.objects.all().order_by('-created_at')
    serializer_class = SourceSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=True, methods=['post'], url_path='toggle-active')
    def toggle_active(self, request, pk=None):
        source = self.get_object()
        source.is_active = not source.is_active
        source.save(update_fields=['is_active'])
        return Response(SourceSerializer(source).data)


class DestinationViewSet(viewsets.ModelViewSet):
    queryset = Destination.objects.all().order_by('-created_at')
    serializer_class = DestinationSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=True, methods=['post'], url_path='toggle-active')
    def toggle_active(self, request, pk=None):
        dest = self.get_object()
        dest.is_active = not dest.is_active
        dest.save(update_fields=['is_active'])
        return Response(DestinationSerializer(dest).data)


class RouteViewSet(viewsets.ModelViewSet):
    queryset = Route.objects.select_related('source', 'destination').order_by('priority')
    serializer_class = RouteSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        source_id = self.request.query_params.get('source')
        if source_id:
            qs = qs.filter(source_id=source_id)
        return qs

    @action(detail=True, methods=['post'], url_path='toggle-active')
    def toggle_active(self, request, pk=None):
        route = self.get_object()
        route.is_active = not route.is_active
        route.save(update_fields=['is_active'])
        return Response(RouteSerializer(route).data)


class WebhookDeliveryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = WebhookDelivery.objects.select_related('source').order_by('-received_at')
    serializer_class = WebhookDeliverySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        if s := self.request.query_params.get('status'):
            qs = qs.filter(status=s)
        if src := self.request.query_params.get('source'):
            qs = qs.filter(source_id=src)
        return qs


class MetricsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        recent = MetricPoint.objects.order_by('-timestamp')[:100]
        latest: dict = {}
        for point in reversed(list(recent)):
            latest[point.name] = point.value
        return Response({
            'latest': latest,
            'history': MetricPointSerializer(recent, many=True).data,
        })
