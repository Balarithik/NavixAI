"""
Navigation API URLs for NavixAI.
"""

from django.urls import path
from .views import (
    BuildingEntranceListView,
    BuildingFloorDetailView,
    BuildingFloorsView,
    BuildingListView,
    CampusBuildingDetailView,
    CampusBuildingListView,
    CampusFacilityListView,
    CampusSpaceListView,
    FloorListView,
    OutdoorQRCodeImageView,
    NodeListView,
    NodeDetailView,
    OutdoorNodeListView,
    OutdoorEdgeListView,
    OutdoorRouteView,
    ScanQRCodeView,
    RouteCalculationView,
    QRCodeImageView,
    UnifiedRouteView,
    UnifiedSearchView,
)

urlpatterns = [
    # Existing indoor MVP endpoints (preserved)
    path('building/', BuildingListView.as_view(), name='api-building'),
    path('floors/', FloorListView.as_view(), name='api-floors'),
    path('nodes/', NodeListView.as_view(), name='api-nodes'),
    path('nodes/<str:node_id>/', NodeDetailView.as_view(), name='api-node-detail'),
    path('scan/', ScanQRCodeView.as_view(), name='api-scan'),
    path('routes/', RouteCalculationView.as_view(), name='api-routes'),
    path('qr/<str:node_id>/', QRCodeImageView.as_view(), name='api-qr-image'),
    path('qr/outdoor/<str:node_id>/', OutdoorQRCodeImageView.as_view(), name='api-qr-outdoor-image'),
    # Campus / outdoor extension
    path('campus/buildings/', CampusBuildingListView.as_view(), name='api-campus-buildings'),
    path('campus/buildings/<str:code>/', CampusBuildingDetailView.as_view(), name='api-campus-building-detail'),
    path('buildings/<str:code>/floors/', BuildingFloorsView.as_view(), name='api-building-floors'),
    path('buildings/<str:code>/floors/<str:floor>/', BuildingFloorDetailView.as_view(), name='api-building-floor-detail'),
    path('entrances/', BuildingEntranceListView.as_view(), name='api-entrances'),
    path('facilities/', CampusFacilityListView.as_view(), name='api-facilities'),
    path('spaces/', CampusSpaceListView.as_view(), name='api-spaces'),
    path('outdoor/nodes/', OutdoorNodeListView.as_view(), name='api-outdoor-nodes'),
    path('outdoor/edges/', OutdoorEdgeListView.as_view(), name='api-outdoor-edges'),
    path('outdoor/route/', OutdoorRouteView.as_view(), name='api-outdoor-route'),
    path('search/', UnifiedSearchView.as_view(), name='api-search'),
    path('navigation/route/', UnifiedRouteView.as_view(), name='api-navigation-route'),
]
