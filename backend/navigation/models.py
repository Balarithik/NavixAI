from django.db import models


class Building(models.Model):
    CATEGORY_CHOICES = (
        ('academic', 'Academic Block'),
        ('facility', 'Facility'),
        ('administration', 'Administration'),
        ('hostel', 'Hostel'),
        ('gate', 'Campus Gate'),
        ('landmark', 'Landmark'),
        ('other', 'Other'),
    )

    name = models.CharField(max_length=128)
    code = models.CharField(max_length=32, unique=True)
    description = models.TextField(blank=True, default='')
    category = models.CharField(max_length=32, choices=CATEGORY_CHOICES, default='academic')
    # Geographic campus position (CampusNav-owned data, not scraped)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    entrance_latitude = models.FloatField(null=True, blank=True)
    entrance_longitude = models.FloatField(null=True, blank=True)
    # Coordinate provenance: verified (field GPS) | official (KARE document) |
    # synthetic (dev placeholder — must not be presented as surveyed data)
    SOURCE_CHOICES = (
        ('verified', 'Verified'),
        ('official', 'Official document'),
        ('synthetic', 'Synthetic placeholder'),
        ('unknown', 'Unknown'),
    )
    source = models.CharField(max_length=16, choices=SOURCE_CHOICES, default='unknown')
    coordinate_verified = models.BooleanField(default=False)
    is_navigable = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.code})"


class BuildingEntrance(models.Model):
    """Bridge entity: outdoor campus node <-> indoor entrance node."""
    entrance_id = models.CharField(max_length=64, unique=True, db_index=True)
    building = models.ForeignKey(Building, related_name='entrances', on_delete=models.CASCADE)
    name = models.CharField(max_length=128, default='Main Entrance')
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    # Outdoor graph node id (OutdoorNode.node_id) at this entrance
    outdoor_node_id = models.CharField(max_length=64, blank=True, default='')
    # Indoor graph node id (Node.node_id) just inside this entrance
    indoor_node_id = models.CharField(max_length=64, blank=True, default='')
    is_accessible = models.BooleanField(default=True)
    source = models.CharField(max_length=16, default='unknown')
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.building.code} entrance {self.entrance_id}"


class OutdoorNode(models.Model):
    NODE_TYPES = (
        ('gate', 'Campus Gate'),
        ('junction', 'Path Junction'),
        ('walkway', 'Walkway Point'),
        ('building_entrance', 'Building Entrance'),
        ('facility', 'Facility'),
        ('landmark', 'Landmark'),
    )

    node_id = models.CharField(max_length=64, unique=True, db_index=True)
    name = models.CharField(max_length=128)
    type = models.CharField(max_length=32, choices=NODE_TYPES, default='walkway')
    building = models.ForeignKey(
        Building, related_name='outdoor_nodes', on_delete=models.SET_NULL,
        null=True, blank=True,
    )
    latitude = models.FloatField()
    longitude = models.FloatField()
    # QR payload for outdoor positioning (auto-generated as CAMPUSNAV|OUTDOOR|<node_id>
    # unless the CSV provides an explicit value). Null = not yet assigned.
    qr_code = models.CharField(max_length=128, unique=True, null=True, blank=True, db_index=True)
    is_accessible = models.BooleanField(default=True)
    source = models.CharField(max_length=16, default='unknown')
    coordinate_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_checkpoint = models.BooleanField(default=False)

    class Meta:
        ordering = ['node_id']

    def __str__(self):
        return f"{self.name} [{self.node_id}]"


class OutdoorEdge(models.Model):
    MOVEMENT_TYPES = (
        ('walk', 'Walk'),
        ('accessible_walk', 'Accessible Walk'),
    )

    edge_id = models.CharField(max_length=64, unique=True, db_index=True, null=True, blank=True)
    from_node = models.ForeignKey(OutdoorNode, related_name='outgoing_edges', on_delete=models.CASCADE)
    to_node = models.ForeignKey(OutdoorNode, related_name='incoming_edges', on_delete=models.CASCADE)
    distance_m = models.FloatField(help_text='Distance in metres')
    accessible = models.BooleanField(default=True)
    movement_type = models.CharField(max_length=32, choices=MOVEMENT_TYPES, default='walk')
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('from_node', 'to_node', 'movement_type')

    def __str__(self):
        return f"{self.from_node.node_id} -> {self.to_node.node_id} ({self.distance_m:.0f}m)"


class CampusFacility(models.Model):
    """Map/search POI. May link to a Building, but is never a graph node itself."""
    facility_id = models.CharField(max_length=64, unique=True, db_index=True)
    name = models.CharField(max_length=128)
    category = models.CharField(max_length=32, default='facility')
    building = models.ForeignKey(
        Building, related_name='facilities', on_delete=models.SET_NULL,
        null=True, blank=True,
    )
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    source = models.CharField(max_length=16, default='unknown')
    coordinate_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} [{self.facility_id}]"


class CampusSpace(models.Model):
    """Contextual campus space (parking, landscape, water...). Map/search context only."""
    space_id = models.CharField(max_length=64, unique=True, db_index=True)
    name = models.CharField(max_length=128)
    space_type = models.CharField(max_length=32, default='other')
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    description = models.TextField(blank=True, default='')
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} [{self.space_id}]"


class Floor(models.Model):
    building = models.ForeignKey(Building, related_name='floors', on_delete=models.CASCADE)
    floor_number = models.IntegerField()
    name = models.CharField(max_length=64)
    map_width = models.FloatField(default=100.0)
    map_height = models.FloatField(default=100.0)
    # Optional floor-plan asset (SVG/PNG) served as the visual layer.
    # Node x/y coordinates are expressed in the same unit space as
    # map_width/map_height, so nodes always align with the asset.
    map_asset = models.CharField(max_length=255, blank=True, default='')
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
        ('door', 'Door'),
        ('junction', 'Junction'),
        ('corridor', 'Corridor'),
        ('stair', 'Staircase'),
        ('lift', 'Lift'),
        ('amenity', 'Amenity'),
        ('office', 'Office'),
        ('lab', 'Lab'),
        ('hall', 'Hall'),
        ('restroom', 'Restroom'),
        ('facility', 'Facility'),
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

    edge_id = models.CharField(max_length=64, unique=True, db_index=True, null=True, blank=True)
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
