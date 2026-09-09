"""
API Views for NavixAI navigation system.
"""

import os
from django.http import HttpResponse, Http404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics

from .models import Building, Floor, Node, Edge
from .serializers import (
    BuildingSerializer,
    FloorSerializer,
    NodeSerializer,
    EdgeSerializer,
    ScanRequestSerializer,
)
from .qr.validator import validate_and_decode_qr, InvalidQRCodeError
from .qr.generator import QRCodeGenerator
from .routing.route_engine import RouteEngine


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
    Validates scanned QR code payload and returns node information.
    POST /api/scan/
    { "payload": "CAMPUSNAV:F1_N01" }
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
            node = validate_and_decode_qr(payload)
            return Response({
                'valid': True,
                'node_id': node.node_id,
                'name': node.name,
                'floor': node.floor.floor_number,
                'floor_name': node.floor.name,
                'type': node.type,
                'x': node.x,
                'y': node.y,
            }, status=status.HTTP_200_OK)
        except InvalidQRCodeError as e:
            return Response({
                'valid': False,
                'error': str(e)
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
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
        except Exception as e:
            return Response({'error': f"Failed to compute route: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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
