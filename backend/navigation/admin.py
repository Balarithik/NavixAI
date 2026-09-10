from django.contrib import admin
from .models import (
    Building, BuildingEntrance, CampusFacility, CampusSpace, Floor, Node,
    Edge, OutdoorEdge, OutdoorNode, QRCode,
)


@admin.register(Building)
class BuildingAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'category', 'is_navigable', 'is_active')
    search_fields = ('name', 'code')
    list_filter = ('category', 'is_navigable', 'is_active')


@admin.register(BuildingEntrance)
class BuildingEntranceAdmin(admin.ModelAdmin):
    list_display = ('entrance_id', 'building', 'outdoor_node_id', 'indoor_node_id', 'is_active')
    search_fields = ('entrance_id', 'building__code', 'outdoor_node_id', 'indoor_node_id')


@admin.register(CampusFacility)
class CampusFacilityAdmin(admin.ModelAdmin):
    list_display = ('facility_id', 'name', 'category', 'building', 'source', 'is_active')
    list_filter = ('category', 'source', 'is_active')
    search_fields = ('facility_id', 'name')


@admin.register(CampusSpace)
class CampusSpaceAdmin(admin.ModelAdmin):
    list_display = ('space_id', 'name', 'space_type', 'is_active')
    list_filter = ('space_type', 'is_active')
    search_fields = ('space_id', 'name')


@admin.register(OutdoorNode)
class OutdoorNodeAdmin(admin.ModelAdmin):
    list_display = ('node_id', 'name', 'type', 'building', 'is_checkpoint', 'is_active')
    list_filter = ('type', 'is_checkpoint', 'is_active')
    search_fields = ('node_id', 'name')


@admin.register(OutdoorEdge)
class OutdoorEdgeAdmin(admin.ModelAdmin):
    list_display = ('from_node', 'to_node', 'distance_m', 'movement_type', 'is_active')
    list_filter = ('movement_type', 'is_active')


@admin.register(Floor)
class FloorAdmin(admin.ModelAdmin):
    list_display = ('building', 'floor_number', 'name')
    list_filter = ('building', 'floor_number')
    ordering = ('building', 'floor_number')


@admin.register(Node)
class NodeAdmin(admin.ModelAdmin):
    list_display = ('node_id', 'name', 'type', 'floor', 'block', 'x', 'y', 'qr_code', 'is_checkpoint', 'is_active')
    list_filter = ('floor__building', 'floor', 'type', 'is_checkpoint', 'is_active')
    search_fields = ('node_id', 'name', 'qr_code')
    ordering = ('floor', 'node_id')


@admin.register(Edge)
class EdgeAdmin(admin.ModelAdmin):
    list_display = ('from_node', 'to_node', 'distance', 'movement_type', 'accessible', 'is_active')
    list_filter = ('movement_type', 'accessible', 'is_active')
    search_fields = ('from_node__node_id', 'from_node__name', 'to_node__node_id', 'to_node__name')


@admin.register(QRCode)
class QRCodeAdmin(admin.ModelAdmin):
    list_display = ('node', 'payload', 'image_path', 'created_at')
    search_fields = ('node__node_id', 'node__name', 'payload')
