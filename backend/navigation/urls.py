"""
Navigation API URLs for NavixAI.
"""

from django.urls import path
from .views import (
    BuildingListView,
    FloorListView,
    NodeListView,
    NodeDetailView,
    ScanQRCodeView,
    RouteCalculationView,
    QRCodeImageView,
)

urlpatterns = [
    path('building/', BuildingListView.as_view(), name='api-building'),
    path('floors/', FloorListView.as_view(), name='api-floors'),
    path('nodes/', NodeListView.as_view(), name='api-nodes'),
    path('nodes/<str:node_id>/', NodeDetailView.as_view(), name='api-node-detail'),
    path('scan/', ScanQRCodeView.as_view(), name='api-scan'),
    path('routes/', RouteCalculationView.as_view(), name='api-routes'),
    path('qr/<str:node_id>/', QRCodeImageView.as_view(), name='api-qr-image'),
]
