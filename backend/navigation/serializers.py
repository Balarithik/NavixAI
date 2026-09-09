"""
Django REST Framework serializers for NavixAI.
"""

from rest_framework import serializers
from .models import Building, Floor, Node, Edge, QRCode


class FloorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Floor
        fields = ['id', 'floor_number', 'name', 'map_width', 'map_height']


class BuildingSerializer(serializers.ModelSerializer):
    floors = FloorSerializer(many=True, read_only=True)

    class Meta:
        model = Building
        fields = ['id', 'name', 'code', 'description', 'floors']


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
