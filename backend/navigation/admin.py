from django.contrib import admin
from .models import Building, Floor, Node, Edge, QRCode


@admin.register(Building)
class BuildingAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'created_at')
    search_fields = ('name', 'code')


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
