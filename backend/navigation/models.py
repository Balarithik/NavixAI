from django.db import models


class Building(models.Model):
    name = models.CharField(max_length=128)
    code = models.CharField(max_length=32, unique=True)
    description = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.code})"


class Floor(models.Model):
    building = models.ForeignKey(Building, related_name='floors', on_delete=models.CASCADE)
    floor_number = models.IntegerField()
    name = models.CharField(max_length=64)
    map_width = models.FloatField(default=100.0)
    map_height = models.FloatField(default=100.0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('building', 'floor_number')
        ordering = ['floor_number']

    def __str__(self):
        return f"{self.building.code} - Floor {self.floor_number} ({self.name})"


class Node(models.Model):
    NODE_TYPES = (
        ('entrance', 'Entrance'),
        ('room', 'Room'),
        ('junction', 'Junction'),
        ('corridor', 'Corridor'),
        ('stair', 'Staircase'),
        ('lift', 'Lift'),
        ('amenity', 'Amenity'),
        ('office', 'Office'),
        ('lab', 'Lab'),
        ('restroom', 'Restroom'),
    )

    node_id = models.CharField(max_length=64, unique=True, db_index=True)
    building = models.ForeignKey(Building, related_name='nodes', on_delete=models.CASCADE)
    block = models.CharField(max_length=32, default='1')
    name = models.CharField(max_length=128)
    type = models.CharField(max_length=32, choices=NODE_TYPES, default='room')
    floor = models.ForeignKey(Floor, related_name='nodes', on_delete=models.CASCADE)
    x = models.FloatField(help_text="X coordinate on floor plan (0-100 or pixels)")
    y = models.FloatField(help_text="Y coordinate on floor plan (0-100 or pixels)")
    qr_code = models.CharField(max_length=128, unique=True, db_index=True)
    is_active = models.BooleanField(default=True)
    is_checkpoint = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['floor__floor_number', 'node_id']
        indexes = [
            models.Index(fields=['node_id']),
            models.Index(fields=['qr_code']),
            models.Index(fields=['floor', 'type']),
        ]

    def __str__(self):
        return f"{self.name} [{self.node_id}] (Floor {self.floor.floor_number})"


class Edge(models.Model):
    MOVEMENT_TYPES = (
        ('walk', 'Walk'),
        ('stairs', 'Stairs'),
        ('lift', 'Lift'),
    )

    from_node = models.ForeignKey(Node, related_name='outgoing_edges', on_delete=models.CASCADE)
    to_node = models.ForeignKey(Node, related_name='incoming_edges', on_delete=models.CASCADE)
    distance = models.FloatField(help_text="Distance in metres or coordinate units")
    accessible = models.BooleanField(default=True, help_text="True if wheelchair accessible")
    movement_type = models.CharField(max_length=32, choices=MOVEMENT_TYPES, default='walk')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('from_node', 'to_node', 'movement_type')
        indexes = [
            models.Index(fields=['from_node', 'is_active']),
            models.Index(fields=['to_node', 'is_active']),
            models.Index(fields=['movement_type']),
        ]

    def __str__(self):
        return f"{self.from_node.node_id} -> {self.to_node.node_id} ({self.movement_type}, {self.distance:.1f}m)"


class QRCode(models.Model):
    node = models.OneToOneField(Node, related_name='qr_detail', on_delete=models.CASCADE)
    payload = models.CharField(max_length=255, unique=True)
    image_path = models.CharField(max_length=255, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"QR for {self.node.node_id}: {self.payload}"
