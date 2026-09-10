"""
Django REST Framework serializers for NavixAI.
"""

from rest_framework import serializers
from .models import (
    Building, BuildingEntrance, CampusFacility, CampusSpace, Floor, Node,
    Edge, OutdoorEdge, OutdoorNode, QRCode,
)


class FloorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Floor
        fields = ['id', 'floor_number', 'name', 'map_width', 'map_height', 'map_asset']


class BuildingEntranceSerializer(serializers.ModelSerializer):
    building_code = serializers.CharField(source='building.code', read_only=True)

    class Meta:
        model = BuildingEntrance
        fields = [
            'id', 'entrance_id', 'name', 'building_code', 'latitude', 'longitude',
            'outdoor_node_id', 'indoor_node_id', 'is_accessible', 'source', 'is_active',
        ]


class BuildingSerializer(serializers.ModelSerializer):
    floors = FloorSerializer(many=True, read_only=True)
    entrances = BuildingEntranceSerializer(many=True, read_only=True)

    class Meta:
        model = Building
        fields = [
            'id', 'name', 'code', 'description', 'category',
            'latitude', 'longitude', 'entrance_latitude', 'entrance_longitude',
            'source', 'coordinate_verified',
            'is_navigable', 'is_active', 'floors', 'entrances',
        ]


class OutdoorNodeSerializer(serializers.ModelSerializer):
    building_code = serializers.CharField(source='building.code', read_only=True, default=None)

    class Meta:
        model = OutdoorNode
        fields = [
            'id', 'node_id', 'name', 'type', 'building_code',
            'latitude', 'longitude', 'qr_code', 'is_accessible', 'source',
            'coordinate_verified', 'is_checkpoint', 'is_active',
        ]


class CampusFacilitySerializer(serializers.ModelSerializer):
    building_code = serializers.CharField(source='building.code', read_only=True, default=None)
    building_name = serializers.CharField(source='building.name', read_only=True, default=None)

    class Meta:
        model = CampusFacility
        fields = [
            'id', 'facility_id', 'name', 'category', 'building_code', 'building_name',
            'latitude', 'longitude', 'source', 'coordinate_verified', 'is_active',
        ]


class CampusSpaceSerializer(serializers.ModelSerializer):
    class Meta:
        model = CampusSpace
        fields = [
            'id', 'space_id', 'name', 'space_type',
            'latitude', 'longitude', 'description', 'is_active',
        ]


class OutdoorEdgeSerializer(serializers.ModelSerializer):
    from_node_id = serializers.CharField(source='from_node.node_id', read_only=True)
    to_node_id = serializers.CharField(source='to_node.node_id', read_only=True)

    class Meta:
        model = OutdoorEdge
        fields = [
            'id', 'from_node', 'to_node', 'from_node_id', 'to_node_id',
            'distance_m', 'accessible', 'movement_type', 'is_active',
        ]


class NodeSerializer(serializers.ModelSerializer):
    floor_number = serializers.IntegerField(source='floor.floor_number', read_only=True)
    floor_name = serializers.CharField(source='floor.name', read_only=True)
    building_code = serializers.CharField(source='building.code', read_only=True)

    class Meta:
        model = Node
        fields = [
            'id',
            'node_id',
            'name',
            'type',
            'block',
            'floor',
            'floor_number',
            'floor_name',
            'building_code',
            'x',
            'y',
            'qr_code',
            'is_checkpoint',
            'is_active',
        ]


class EdgeSerializer(serializers.ModelSerializer):
    from_node_id = serializers.CharField(source='from_node.node_id', read_only=True)
    to_node_id = serializers.CharField(source='to_node.node_id', read_only=True)

    class Meta:
        model = Edge
        fields = [
            'id',
            'from_node',
            'to_node',
            'from_node_id',
            'to_node_id',
            'distance',
            'accessible',
            'movement_type',
            'is_active',
        ]


class ScanRequestSerializer(serializers.Serializer):
    payload = serializers.CharField(required=True, trim_whitespace=True)


class ScanResponseSerializer(serializers.Serializer):
    valid = serializers.BooleanField()
    node_id = serializers.CharField()
    name = serializers.CharField()
    floor = serializers.IntegerField()
    floor_name = serializers.CharField()
    type = serializers.CharField()
    x = serializers.FloatField()
    y = serializers.FloatField()
