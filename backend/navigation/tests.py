import io
from django.test import TestCase, Client
from django.urls import reverse
from navigation.models import Building, Floor, Node, Edge, QRCode
from navigation.importer.validator import validate_csv_rows, CSVValidationError
from navigation.importer.csv_parser import BuildingCSVImporter
from navigation.routing.route_engine import RouteEngine
from navigation.qr.validator import validate_and_decode_qr, InvalidQRCodeError


class CSVValidatorTests(TestCase):
    def test_valid_csv_rows(self):
        rows = [
            {'node_id': 'F1_N01', 'block': '1', 'name': 'Entrance', 'type': 'entrance', 'floor': '1', 'x': '10', 'y': '20', 'qr_code': 'NAVIXAI:F1_N01'},
            {'node_id': 'F1_N02', 'block': '1', 'name': 'Room 101', 'type': 'room', 'floor': '1', 'x': '30', 'y': '20', 'qr_code': 'NAVIXAI:F1_N02'},
        ]
        clean, errors = validate_csv_rows(rows)
        self.assertEqual(len(errors), 0)
        self.assertEqual(len(clean), 2)
        self.assertEqual(clean[0]['floor'], 1)

    def test_duplicate_node_id_rejected(self):
        rows = [
            {'node_id': 'F1_N01', 'block': '1', 'name': 'Entrance', 'type': 'entrance', 'floor': '1', 'x': '10', 'y': '20', 'qr_code': 'QR1'},
            {'node_id': 'F1_N01', 'block': '1', 'name': 'Duplicate', 'type': 'room', 'floor': '1', 'x': '20', 'y': '20', 'qr_code': 'QR2'},
        ]
        clean, errors = validate_csv_rows(rows)
        self.assertTrue(any('Duplicate node_id' in e for e in errors))

    def test_invalid_floor_rejected(self):
        rows = [
            {'node_id': 'F1_N01', 'block': '1', 'name': 'Entrance', 'type': 'entrance', 'floor': '-1', 'x': '10', 'y': '20', 'qr_code': 'QR1'},
        ]
        clean, errors = validate_csv_rows(rows)
        self.assertTrue(any('Floor must be a positive integer' in e for e in errors))

    def test_invalid_node_type_rejected(self):
        rows = [
            {'node_id': 'F1_N01', 'block': '1', 'name': 'Entrance', 'type': 'spaceship', 'floor': '1', 'x': '10', 'y': '20', 'qr_code': 'QR1'},
        ]
        clean, errors = validate_csv_rows(rows)
        self.assertTrue(any('Unknown node type' in e for e in errors))


class RoutingAndAPITests(TestCase):
    def setUp(self):
        self.client = Client()
        self.building = Building.objects.create(name="Tech Tower", code="MAIN")
        self.f1 = Floor.objects.create(building=self.building, floor_number=1, name="Floor 1")
        self.f2 = Floor.objects.create(building=self.building, floor_number=2, name="Floor 2")

        self.n1 = Node.objects.create(
            node_id="F1_N01", building=self.building, block="1", name="Main Entrance",
            type="entrance", floor=self.f1, x=10.0, y=85.0, qr_code="CAMPUSNAV:F1_N01", is_checkpoint=True
        )
        self.n2 = Node.objects.create(
            node_id="F1_N02", building=self.building, block="1", name="Reception",
            type="amenity", floor=self.f1, x=20.0, y=85.0, qr_code="CAMPUSNAV:F1_N02"
        )
        self.n_stair1 = Node.objects.create(
            node_id="F1_N09", building=self.building, block="1", name="Staircase A",
            type="stair", floor=self.f1, x=35.0, y=35.0, qr_code="CAMPUSNAV:F1_N09", is_checkpoint=True
        )
        self.n_lift1 = Node.objects.create(
            node_id="F1_N10", building=self.building, block="1", name="Lift A",
            type="lift", floor=self.f1, x=75.0, y=35.0, qr_code="CAMPUSNAV:F1_N10", is_checkpoint=True
        )

        self.n_stair2 = Node.objects.create(
            node_id="F2_N01", building=self.building, block="1", name="Staircase A",
            type="stair", floor=self.f2, x=35.0, y=75.0, qr_code="CAMPUSNAV:F2_N01", is_checkpoint=True
        )
        self.n_lift2 = Node.objects.create(
            node_id="F2_N02", building=self.building, block="1", name="Lift A",
            type="lift", floor=self.f2, x=75.0, y=75.0, qr_code="CAMPUSNAV:F2_N02", is_checkpoint=True
        )
        self.n_lab = Node.objects.create(
            node_id="F2_N08", building=self.building, block="1", name="Lab 1",
            type="room", floor=self.f2, x=20.0, y=25.0, qr_code="CAMPUSNAV:F2_N08"
        )

        # Floor 1 internal edges
        Edge.objects.create(from_node=self.n1, to_node=self.n2, distance=10.0, movement_type='walk')
        Edge.objects.create(from_node=self.n2, to_node=self.n1, distance=10.0, movement_type='walk')
        Edge.objects.create(from_node=self.n2, to_node=self.n_stair1, distance=25.0, movement_type='walk')
        Edge.objects.create(from_node=self.n_stair1, to_node=self.n2, distance=25.0, movement_type='walk')
        Edge.objects.create(from_node=self.n2, to_node=self.n_lift1, distance=25.0, movement_type='walk')
        Edge.objects.create(from_node=self.n_lift1, to_node=self.n2, distance=25.0, movement_type='walk')

        # Floor 2 internal edges
        Edge.objects.create(from_node=self.n_stair2, to_node=self.n_lab, distance=20.0, movement_type='walk')
        Edge.objects.create(from_node=self.n_lab, to_node=self.n_stair2, distance=20.0, movement_type='walk')
        Edge.objects.create(from_node=self.n_lift2, to_node=self.n_lab, distance=25.0, movement_type='walk')
        Edge.objects.create(from_node=self.n_lab, to_node=self.n_lift2, distance=25.0, movement_type='walk')

        # Inter-floor transitions
        # Stairs: F1_N09 <-> F2_N01
        Edge.objects.create(from_node=self.n_stair1, to_node=self.n_stair2, distance=15.0, movement_type='stairs', accessible=False)
        Edge.objects.create(from_node=self.n_stair2, to_node=self.n_stair1, distance=15.0, movement_type='stairs', accessible=False)

        # Lift: F1_N10 <-> F2_N02
        Edge.objects.create(from_node=self.n_lift1, to_node=self.n_lift2, distance=10.0, movement_type='lift', accessible=True)
        Edge.objects.create(from_node=self.n_lift2, to_node=self.n_lift1, distance=10.0, movement_type='lift', accessible=True)

    def test_qr_validation(self):
        node = validate_and_decode_qr("CAMPUSNAV:F1_N01")
        self.assertEqual(node.node_id, "F1_N01")

        node_fallback = validate_and_decode_qr("NAVIXAI:F1_N01")
        self.assertEqual(node_fallback.node_id, "F1_N01")

        with self.assertRaises(InvalidQRCodeError):
            validate_and_decode_qr("UNKNOWN_CODE")

    def test_same_floor_route(self):
        engine = RouteEngine()
        route = engine.calculate_route('F1_N01', 'F1_N02')
        self.assertTrue(route['success'])
        self.assertEqual(route['floorsCrossed'], 0)
        self.assertEqual([p['node_id'] for p in route['path']], ['F1_N01', 'F1_N02'])

    def test_multi_floor_lift_mode(self):
        engine = RouteEngine()
        route = engine.calculate_route('F1_N01', 'F2_N08', mode='lift')
        self.assertTrue(route['success'])
        self.assertEqual(route['floorsCrossed'], 1)
        self.assertEqual(route['verticalMode'], 'lift')
        path_ids = [p['node_id'] for p in route['path']]
        self.assertIn('F1_N10', path_ids)
        self.assertIn('F2_N02', path_ids)
        self.assertNotIn('F1_N09', path_ids)

    def test_multi_floor_stairs_mode(self):
        engine = RouteEngine()
        route = engine.calculate_route('F1_N01', 'F2_N08', mode='stairs')
        self.assertTrue(route['success'])
        self.assertEqual(route['floorsCrossed'], 1)
        self.assertEqual(route['verticalMode'], 'stairs')
        path_ids = [p['node_id'] for p in route['path']]
        self.assertIn('F1_N09', path_ids)
        self.assertIn('F2_N01', path_ids)
        self.assertNotIn('F1_N10', path_ids)

    def test_api_scan_endpoint(self):
        response = self.client.post(
            reverse('api-scan'),
            data={'payload': 'CAMPUSNAV:F1_N01'},
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['valid'])
        self.assertEqual(data['node_id'], 'F1_N01')

    def test_api_routes_endpoint(self):
        response = self.client.get(reverse('api-routes') + '?from=F1_N01&to=F2_N08&mode=lift')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['verticalMode'], 'lift')
        self.assertTrue(len(data['instructions']) > 0)

    def test_api_nodes_endpoint(self):
        response = self.client.get(reverse('api-nodes') + '?floor=1')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 4)

    def test_api_qr_image_endpoint(self):
        response = self.client.get(reverse('api-qr-image', kwargs={'node_id': 'F1_N01'}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'image/png')
