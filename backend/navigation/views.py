"""
API Views for NavixAI navigation system.
"""

import os
import logging
from django.http import HttpResponse, Http404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics

from .models import Building, BuildingEntrance, CampusFacility, CampusSpace, Floor, Node, Edge, OutdoorEdge, OutdoorNode
from .serializers import (
    BuildingEntranceSerializer,
    BuildingSerializer,
    CampusFacilitySerializer,
    CampusSpaceSerializer,
    FloorSerializer,
    NodeSerializer,
    EdgeSerializer,
    OutdoorEdgeSerializer,
    OutdoorNodeSerializer,
    ScanRequestSerializer,
)
from .qr.validator import validate_and_decode_qr, validate_location, InvalidQRCodeError
from .qr.generator import QRCodeGenerator
from .routing.route_engine import RouteEngine
from .outdoor.route_engine import OutdoorRouteEngine
from . import navigation_service
from .search_service import search_campus


logger = logging.getLogger(__name__)


class BuildingListView(generics.ListAPIView):
    """Returns list of buildings with nested floors."""
    queryset = Building.objects.prefetch_related('floors').all()
    serializer_class = BuildingSerializer


class FloorListView(generics.ListAPIView):
    """Returns list of building floors."""
    queryset = Floor.objects.all().order_by('floor_number')
    serializer_class = FloorSerializer


class NodeListView(generics.ListAPIView):
    """
    Returns active nodes, optionally filtered by floor number or search query.
    """
    serializer_class = NodeSerializer

    def get_queryset(self):
        qs = Node.objects.filter(is_active=True).select_related('floor', 'building')
        floor_param = self.request.query_params.get('floor')
        type_param = self.request.query_params.get('type')
        query = self.request.query_params.get('q')

        if floor_param:
            try:
                qs = qs.filter(floor__floor_number=int(floor_param))
            except ValueError:
                pass

        if type_param:
            qs = qs.filter(type__iexact=type_param)

        if query:
            qs = qs.filter(name__icontains=query)

        return qs.order_by('floor__floor_number', 'name')


class NodeDetailView(APIView):
    """Returns detailed information for a single node by node_id."""
    def get(self, request, node_id):
        node = Node.objects.filter(node_id__iexact=node_id, is_active=True).select_related('floor', 'building').first()
        if not node:
            return Response({'error': f"Node '{node_id}' not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(NodeSerializer(node).data)


class ScanQRCodeView(APIView):
    """
    Unified QR validation (outdoor + indoor). Backend is authoritative:
    React must POST the raw payload and use the returned location.
    POST /api/scan/  { "payload": "CAMPUSNAV|OUTDOOR|MAIN_GATE" }
    """
    def post(self, request):
        serializer = ScanRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'valid': False,
                'error': 'Invalid request format. "payload" string is required.'
            }, status=status.HTTP_400_BAD_REQUEST)

        payload = serializer.validated_data['payload']
        try:
            result = validate_location(payload)
            if result['location_type'] == 'outdoor':
                n = result['outdoor_node']
                return Response({
                    'valid': True,
                    'location_type': 'outdoor',
                    'location_id': n.node_id,
                    'node_id': n.node_id,
                    'name': n.name,
                    'type': n.type,
                    'latitude': n.latitude,
                    'longitude': n.longitude,
                    'building_id': n.building.code if n.building else None,
                    'building_name': n.building.name if n.building else None,
                    'floor': None,
                }, status=status.HTTP_200_OK)
            node = result['node']
            return Response({
                'valid': True,
                'location_type': 'indoor',
                'location_id': node.node_id,
                'node_id': node.node_id,
                'name': node.name,
                'floor': node.floor.floor_number,
                'floor_name': node.floor.name,
                'type': node.type,
                'x': node.x,
                'y': node.y,
                'building_id': node.building.code,
                'building_name': node.building.name,
                'qr_payload': node.qr_code,
            }, status=status.HTTP_200_OK)
        except InvalidQRCodeError as e:
            return Response({
                'valid': False,
                'error': str(e)
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception:
            return Response({
                'valid': False,
                'error': 'Unable to process QR code.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class RouteCalculationView(APIView):
    """
    Calculates shortest path using Dijkstra with lift vs stairs support.
    GET /api/routes/?from=F1_N01&to=F2_N08&mode=lift
    """
    def get(self, request):
        from_id = request.query_params.get('from')
        to_id = request.query_params.get('to')
        mode = request.query_params.get('mode', 'any').lower()

        if not from_id or not to_id:
            return Response({
                'error': "Both 'from' and 'to' query parameters are required."
            }, status=status.HTTP_400_BAD_REQUEST)

        if mode not in ('any', 'lift', 'stairs'):
            return Response({
                'error': "Invalid mode parameter. Allowed values: 'any', 'lift', 'stairs'."
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            engine = RouteEngine()
            route_data = engine.calculate_route(from_id, to_id, mode=mode)
            if not route_data.get('success', False):
                return Response(route_data, status=status.HTTP_404_NOT_FOUND)
            return Response(route_data, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_404_NOT_FOUND)
        except Exception:
            logger.exception('Indoor route calculation failed')
            return Response({'error': 'Unable to compute route.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CampusBuildingListView(generics.ListAPIView):
    """Campus buildings with geo + entrances (drives outdoor map markers)."""
    serializer_class = BuildingSerializer

    def get_queryset(self):
        return Building.objects.filter(is_active=True).prefetch_related('floors', 'entrances').order_by('name')


class CampusBuildingDetailView(APIView):
    """Single building with floors and entrances (drives bottom sheet)."""
    def get(self, request, code):
        building = Building.objects.filter(code__iexact=code, is_active=True).prefetch_related('floors', 'entrances').first()
        if not building:
            return Response({'error': f"Building '{code}' not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(BuildingSerializer(building).data)


class BuildingFloorsView(generics.ListAPIView):
    """Floors for a building (dynamic floor selector)."""
    serializer_class = FloorSerializer

    def get_queryset(self):
        code = self.kwargs.get('code')
        return Floor.objects.filter(building__code__iexact=code).order_by('floor_number')


class BuildingFloorDetailView(APIView):
    """One floor with map metadata + nodes + edges (drives IndoorMap).

    GET /api/buildings/<code>/floors/<floor>/
    """
    def get(self, request, code, floor):
        building = Building.objects.filter(code__iexact=code, is_active=True).first()
        if not building:
            return Response({'error': f"Building '{code}' not found."}, status=status.HTTP_404_NOT_FOUND)
        try:
            floor_number = int(floor)
        except (ValueError, TypeError):
            return Response({'error': f"Invalid floor '{floor}'."}, status=status.HTTP_400_BAD_REQUEST)
        floor_obj = Floor.objects.filter(building=building, floor_number=floor_number).first()
        if not floor_obj:
            return Response(
                {'error': f"Floor {floor_number} not found in building '{code}'."},
                status=status.HTTP_404_NOT_FOUND)
        nodes = Node.objects.filter(floor=floor_obj, is_active=True).select_related('floor', 'building')
        edges = Edge.objects.filter(
            from_node__floor=floor_obj, to_node__floor=floor_obj, is_active=True
        ).select_related('from_node', 'to_node')
        return Response({
            'building': building.code,
            'building_name': building.name,
            'floor': floor_obj.floor_number,
            'floor_name': floor_obj.name,
            'map': {
                'asset': floor_obj.map_asset,
                'width': floor_obj.map_width,
                'height': floor_obj.map_height,
            },
            'nodes': NodeSerializer(nodes, many=True).data,
            'edges': EdgeSerializer(edges, many=True).data,
        })


class BuildingEntranceListView(generics.ListAPIView):
    serializer_class = BuildingEntranceSerializer

    def get_queryset(self):
        qs = BuildingEntrance.objects.filter(is_active=True).select_related('building')
        code = self.request.query_params.get('building')
        if code:
            qs = qs.filter(building__code__iexact=code)
        return qs


class CampusFacilityListView(generics.ListAPIView):
    """Facilities/POIs: map + search data (never graph nodes)."""
    serializer_class = CampusFacilitySerializer

    def get_queryset(self):
        qs = CampusFacility.objects.filter(is_active=True).select_related('building')
        category = self.request.query_params.get('category')
        if category:
            qs = qs.filter(category__iexact=category)
        return qs.order_by('name')


class CampusSpaceListView(generics.ListAPIView):
    """Contextual campus spaces: map/search context only."""
    serializer_class = CampusSpaceSerializer

    def get_queryset(self):
        qs = CampusSpace.objects.filter(is_active=True)
        stype = self.request.query_params.get('type')
        if stype:
            qs = qs.filter(space_type__iexact=stype)
        return qs.order_by('name')


class OutdoorEdgeListView(generics.ListAPIView):
    """Active outdoor edges (drives campus road/path rendering)."""
    serializer_class = OutdoorEdgeSerializer

    def get_queryset(self):
        return OutdoorEdge.objects.filter(is_active=True).select_related('from_node', 'to_node')


class OutdoorNodeListView(generics.ListAPIView):
    serializer_class = OutdoorNodeSerializer

    def get_queryset(self):
        qs = OutdoorNode.objects.filter(is_active=True).select_related('building')
        type_param = self.request.query_params.get('type')
        if type_param:
            qs = qs.filter(type__iexact=type_param)
        return qs.order_by('node_id')


class OutdoorRouteView(APIView):
    """GET /api/outdoor/route/?from=MAIN_GATE&to=EIGHTH_BLOCK_ENTRANCE"""
    def get(self, request):
        from_id = request.query_params.get('from')
        to_id = request.query_params.get('to')
        if not from_id or not to_id:
            return Response({'error': "Both 'from' and 'to' are required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            route = OutdoorRouteEngine().calculate_route(from_id, to_id)
            if not route.get('success'):
                return Response(route, status=status.HTTP_404_NOT_FOUND)
            return Response(route)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_404_NOT_FOUND)
        except Exception:
            logger.exception('Outdoor route calculation failed')
            return Response({'error': 'Unable to compute outdoor route.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UnifiedSearchView(APIView):
    """GET /api/search/?q=8th — buildings, outdoor places and indoor rooms."""
    def get(self, request):
        q = request.query_params.get('q', '')
        try:
            limit = int(request.query_params.get('limit', 12))
        except (TypeError, ValueError):
            limit = 12
        limit = max(1, min(limit, 50))
        q = q[:200]
        return Response({'query': q, 'results': search_campus(q, limit=limit)})


class UnifiedRouteView(APIView):
    """
    GET /api/navigation/route/?from_type=outdoor_node&from_id=MAIN_GATE
        &to_type=room&to_id=F2_N08&mode=any
    Also accepts origin lat/lon: &from_lat=..&from_lon=..
    """
    def get(self, request):
        mode = request.query_params.get('mode', 'any').lower()
        if mode not in ('any', 'lift', 'stairs'):
            return Response({'error': "Invalid mode."}, status=status.HTTP_400_BAD_REQUEST)
        origin = {
            'type': request.query_params.get('from_type', ''),
            'node_id': request.query_params.get('from_id', ''),
            'outdoor_node_id': request.query_params.get('from_id', '') if request.query_params.get('from_type') == 'outdoor_node' else '',
            'indoor_node_id': request.query_params.get('from_id', '') if request.query_params.get('from_type') == 'indoor_node' else '',
        }
        if request.query_params.get('from_lat') and request.query_params.get('from_lon'):
            try:
                origin = {'latitude': float(request.query_params['from_lat']),
                          'longitude': float(request.query_params['from_lon'])}
            except ValueError:
                return Response({'error': 'Invalid from_lat/from_lon.'}, status=status.HTTP_400_BAD_REQUEST)
        to_type = (request.query_params.get('to_type') or '').lower()
        to_id = request.query_params.get('to_id', '')
        destination = {'type': to_type, 'id': to_id, 'building_code': '', 'indoor_node_id': '', 'node_id': to_id}
        if to_type == 'room':
            destination['indoor_node_id'] = to_id
        elif to_type == 'building':
            destination['building_code'] = to_id
        elif to_type == 'outdoor_node':
            destination['outdoor_node_id'] = to_id
        if not to_id:
            return Response({'error': "'to_id' is required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            route = navigation_service.calculate_unified_route(origin, destination, mode=mode)
            if route.get('segments') is None and not route.get('success', True):
                return Response(route, status=status.HTTP_404_NOT_FOUND)
            return Response(route)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_404_NOT_FOUND)
        except Exception:
            logger.exception('Unified route calculation failed')
            return Response({'error': 'Unable to compute route.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class QRCodeImageView(APIView):
    """
    Streams a PNG image of the QR code for a given node.
    GET /api/qr/<node_id>/
    """
    def get(self, request, node_id):
        node = Node.objects.filter(node_id__iexact=node_id, is_active=True).first()
        if not node:
            raise Http404(f"Node '{node_id}' not found.")

        generator = QRCodeGenerator()
        buffer = generator.generate_image_stream(node.qr_code or f"NAVIXAI:{node.node_id}")
        return HttpResponse(buffer.getvalue(), content_type="image/png")


class OutdoorQRCodeImageView(APIView):
    """
    Streams a PNG image of the QR code for an outdoor location.
    GET /api/qr/outdoor/<node_id>/
    """
    def get(self, request, node_id):
        from navigation.qr.payloads import outdoor_payload
        node = OutdoorNode.objects.filter(node_id__iexact=node_id, is_active=True).first()
        if not node:
            raise Http404(f"Outdoor location '{node_id}' not found.")
        generator = QRCodeGenerator()
        buffer = generator.generate_image_stream(node.qr_code or outdoor_payload(node.node_id))
        return HttpResponse(buffer.getvalue(), content_type="image/png")
