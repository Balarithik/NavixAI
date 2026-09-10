import io
from django.test import TestCase, Client
from django.urls import reverse
from navigation.models import (
    Building, BuildingEntrance, CampusFacility, CampusSpace, Floor, Node,
    Edge, OutdoorEdge, OutdoorNode, QRCode,
)
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


class OutdoorCampusTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.building = Building.objects.create(
            name='8th Block', code='8TH_BLOCK', category='academic',
            latitude=9.575069, longitude=77.675783,
            entrance_latitude=9.575069, entrance_longitude=77.675783,
        )
        self.gate = OutdoorNode.objects.create(
            node_id='MAIN_GATE', name='Main Gate', type='gate',
            latitude=9.572, longitude=77.674, is_checkpoint=True,
        )
        self.junction = OutdoorNode.objects.create(
            node_id='J1', name='Central Junction', type='junction',
            latitude=9.574, longitude=77.6752, is_checkpoint=True,
        )
        self.entrance = OutdoorNode.objects.create(
            node_id='EIGHTH_ENT', name='8th Block Entrance', type='building_entrance',
            building=self.building, latitude=9.575069, longitude=77.675783,
        )
        OutdoorEdge.objects.create(from_node=self.gate, to_node=self.junction, distance_m=300)
        OutdoorEdge.objects.create(from_node=self.junction, to_node=self.gate, distance_m=300)
        OutdoorEdge.objects.create(from_node=self.junction, to_node=self.entrance, distance_m=150)
        OutdoorEdge.objects.create(from_node=self.entrance, to_node=self.junction, distance_m=150)

    def test_outdoor_route(self):
        from navigation.outdoor.route_engine import OutdoorRouteEngine
        route = OutdoorRouteEngine().calculate_route('MAIN_GATE', 'EIGHTH_ENT')
        self.assertTrue(route['success'])
        self.assertEqual(route['mode'], 'outdoor')
        self.assertGreater(route['distanceMetres'], 0)
        self.assertTrue(len(route['instructions']) >= 2)

    def test_outdoor_route_api(self):
        response = self.client.get(reverse('api-outdoor-route') + '?from=MAIN_GATE&to=EIGHTH_ENT')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['success'])

    def test_campus_buildings_api(self):
        response = self.client.get(reverse('api-campus-buildings'))
        self.assertEqual(response.status_code, 200)
        codes = [b['code'] for b in response.json()]
        self.assertIn('8TH_BLOCK', codes)

    def test_unified_search_finds_building(self):
        response = self.client.get(reverse('api-search') + '?q=8th')
        self.assertEqual(response.status_code, 200)
        types = [r['type'] for r in response.json()['results']]
        self.assertIn('building', types)

    def test_unified_outdoor_route_api(self):
        url = (reverse('api-navigation-route')
               + '?from_type=outdoor_node&from_id=MAIN_GATE&to_type=building&to_id=8TH_BLOCK')
        response = self.client.get(url)
        # 8TH_BLOCK has no mapped entrance in this test DB (no BuildingEntrance row),
        # so the service falls back to the building_entrance outdoor node.
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['mode'], 'outdoor')
        self.assertTrue(data['totalDistanceMetres'] > 0)

    def test_scan_outdoor_canonical_payload(self):
        response = self.client.post(
            reverse('api-scan'), data={'payload': 'CAMPUSNAV|OUTDOOR|MAIN_GATE'},
            content_type='application/json')
        # MAIN_GATE has no qr_code in this test DB; canonical parse still resolves it.
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['valid'])
        self.assertEqual(data['location_type'], 'outdoor')
        self.assertEqual(data['location_id'], 'MAIN_GATE')
        self.assertAlmostEqual(data['latitude'], 9.572)

    def test_scan_outdoor_exact_qr_match(self):
        self.gate.qr_code = 'CAMPUSNAV|OUTDOOR|MAIN_GATE'
        self.gate.save(update_fields=['qr_code'])
        response = self.client.post(
            reverse('api-scan'), data={'payload': 'CAMPUSNAV|OUTDOOR|MAIN_GATE'},
            content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['name'], 'Main Gate')

    def test_scan_invalid_and_unknown_qr(self):
        for payload, status in (('NOT A QR!!!|', 404), ('CAMPUSNAV|OUTDOOR|NOPE', 404),
                                ('CAMPUSNAV|INDOOR|XX|9|NOPE', 404), ('', 400)):
            response = self.client.post(
                reverse('api-scan'), data={'payload': payload},
                content_type='application/json')
            self.assertEqual(response.status_code, status, payload)
            if status != 400:
                self.assertFalse(response.json()['valid'])

    def test_scan_indoor_contract_preserved(self):
        response = self.client.post(
            reverse('api-scan'), data={'payload': 'CAMPUSNAV|INDOOR|MAIN|1|F1_N01'},
            content_type='application/json')
        # No indoor nodes in this test DB → unknown location, not a crash.
        self.assertEqual(response.status_code, 404)
        self.assertFalse(response.json()['valid'])

    def test_outdoor_qr_image_endpoint(self):
        response = self.client.get(reverse('api-qr-outdoor-image', kwargs={'node_id': 'MAIN_GATE'}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'image/png')
        response = self.client.get(reverse('api-qr-outdoor-image', kwargs={'node_id': 'GHOST'}))
        self.assertEqual(response.status_code, 404)

    def test_outdoor_qr_default_assigned_on_import(self):
        from navigation.importer import campus_importer as ci
        c, u = ci.import_outdoor_nodes(
            [{'node_id': 'QR_A', 'name': 'QR Point A', 'type': 'landmark',
              'latitude': '9.5', 'longitude': '77.6'}], 't.csv')
        self.assertEqual((c, u), (1, 0))
        node = OutdoorNode.objects.get(node_id='QR_A')
        self.assertEqual(node.qr_code, 'CAMPUSNAV|OUTDOOR|QR_A')


class CampusImporterTests(TestCase):
    def test_valid_building_upsert_is_idempotent(self):
        from navigation.importer import campus_importer as ci
        rows = [{'building_id': 'T1', 'name': 'Test Block', 'category': 'academic',
                 'latitude': '9.5', 'longitude': '77.6', 'is_active': 'True', 'source': 'synthetic'}]
        c1, u1 = ci.import_building_rows(rows, 't.csv', 'academic')
        c2, u2 = ci.import_building_rows(rows, 't.csv', 'academic')
        self.assertEqual((c1, u1), (1, 0))
        self.assertEqual((c2, u2), (0, 1))
        self.assertEqual(Building.objects.filter(code='T1').count(), 1)

    def test_duplicate_building_id_rejected(self):
        from navigation.importer import campus_importer as ci
        from navigation.importer.campus_importer import CampusImportError
        rows = [
            {'building_id': 'D1', 'name': 'A', 'category': 'academic', 'latitude': '', 'longitude': ''},
            {'building_id': 'D1', 'name': 'B', 'category': 'academic', 'latitude': '', 'longitude': ''},
        ]
        with self.assertRaises(CampusImportError) as ctx:
            ci.import_building_rows(rows, 't.csv', 'academic')
        self.assertTrue(any('duplicate' in e for e in ctx.exception.errors))

    def test_outdoor_node_rejects_unknown_building(self):
        from navigation.importer import campus_importer as ci
        from navigation.importer.campus_importer import CampusImportError
        rows = [{'node_id': 'X1', 'name': 'X', 'type': 'walkway',
                 'latitude': '9.5', 'longitude': '77.6', 'building_id': 'NOPE'}]
        with self.assertRaises(CampusImportError) as ctx:
            ci.import_outdoor_nodes(rows, 't.csv')
        self.assertTrue(any('unknown building_id' in e for e in ctx.exception.errors))

    def test_outdoor_node_rejects_bad_coordinates(self):
        from navigation.importer import campus_importer as ci
        from navigation.importer.campus_importer import CampusImportError
        rows = [{'node_id': 'X2', 'name': 'X', 'type': 'walkway',
                 'latitude': '999', 'longitude': '77.6'}]
        with self.assertRaises(CampusImportError):
            ci.import_outdoor_nodes(rows, 't.csv')

    def test_edge_rejects_unknown_node_and_self_loop(self):
        from navigation.importer import campus_importer as ci
        from navigation.importer.campus_importer import CampusImportError
        OutdoorNode.objects.create(node_id='E_A', name='A', type='walkway',
                                   latitude=9.5, longitude=77.6)
        with self.assertRaises(CampusImportError):
            ci.import_outdoor_edges(
                [{'edge_id': 'E1', 'from_node': 'E_A', 'to_node': 'GHOST'}], 't.csv')
        with self.assertRaises(CampusImportError):
            ci.import_outdoor_edges(
                [{'edge_id': 'E2', 'from_node': 'E_A', 'to_node': 'E_A'}], 't.csv')

    def test_edge_upsert_and_stale_deactivation(self):
        from navigation.importer import campus_importer as ci
        a = OutdoorNode.objects.create(node_id='S_A', name='A', type='walkway',
                                       latitude=9.5, longitude=77.6)
        b = OutdoorNode.objects.create(node_id='S_B', name='B', type='walkway',
                                       latitude=9.5001, longitude=77.6001)
        count, _ = ci.import_outdoor_edges(
            [{'edge_id': 'SE1', 'from_node': 'S_A', 'to_node': 'S_B',
              'bidirectional': 'True'}], 't.csv')
        self.assertEqual(count, 2)
        count2, _ = ci.import_outdoor_edges(
            [{'edge_id': 'SE1', 'from_node': 'S_A', 'to_node': 'S_B',
              'bidirectional': 'True'}], 't.csv')
        self.assertEqual(count2, 2)
        self.assertEqual(OutdoorEdge.objects.filter(edge_id__in=['SE1', 'SE1:R']).count(), 2)
        count3, deactivated = ci.import_outdoor_edges([], 't.csv')
        self.assertEqual(count3, 0)
        self.assertGreaterEqual(deactivated, 2)
        self.assertFalse(OutdoorEdge.objects.get(edge_id='SE1').is_active)

    def test_entrance_rejects_unknown_indoor_node(self):
        from navigation.importer import campus_importer as ci
        from navigation.importer.campus_importer import CampusImportError
        Building.objects.create(name='B', code='EB1')
        with self.assertRaises(CampusImportError):
            ci.import_entrances(
                [{'entrance_id': 'EN1', 'building_id': 'EB1', 'indoor_node_id': 'GHOST'}], 't.csv')


class CampusCatalogTests(TestCase):
    def setUp(self):
        self.client = Client()
        b = Building.objects.create(name='Library', code='LIB', category='facility',
                                    latitude=9.5, longitude=77.6)
        CampusFacility.objects.create(facility_id='FAC_LIB', name='Central Library',
                                      category='facility', building=b,
                                      latitude=9.5, longitude=77.6)
        CampusSpace.objects.create(space_id='SP1', name='South Parking', space_type='parking',
                                   latitude=9.51, longitude=77.61)

    def test_facilities_api(self):
        response = self.client.get(reverse('api-facilities'))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(any(f['facility_id'] == 'FAC_LIB' for f in response.json()))

    def test_spaces_api(self):
        response = self.client.get(reverse('api-spaces'))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(any(s['space_id'] == 'SP1' for s in response.json()))

    def test_outdoor_edges_api(self):
        a = OutdoorNode.objects.create(node_id='RD_A', name='A', type='walkway',
                                       latitude=9.5, longitude=77.6)
        b = OutdoorNode.objects.create(node_id='RD_B', name='B', type='walkway',
                                       latitude=9.5001, longitude=77.6001)
        OutdoorEdge.objects.create(from_node=a, to_node=b, distance_m=15,
                                   edge_id='RD_E1')
        response = self.client.get(reverse('api-outdoor-edges'))
        self.assertEqual(response.status_code, 200)
        rows = response.json()
        self.assertTrue(any(r['from_node_id'] == 'RD_A' and r['to_node_id'] == 'RD_B'
                            for r in rows))

    def test_search_finds_facility_and_space(self):
        for q, want in (('Library', 'facility'), ('Parking', 'space')):
            response = self.client.get(reverse('api-search') + f'?q={q}')
            self.assertEqual(response.status_code, 200)
            self.assertIn(want, [r['type'] for r in response.json()['results']])

    def test_facility_route_snaps_to_graph(self):
        OutdoorNode.objects.create(node_id='F_GATE', name='Gate', type='gate',
                                   latitude=9.5, longitude=77.6)
        url = (reverse('api-navigation-route')
               + '?from_type=outdoor_node&from_id=F_GATE&to_type=facility&to_id=FAC_LIB')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['mode'], 'outdoor')


def _make_indoor_building(code, floors=2):
    b = Building.objects.create(name=code, code=code, category='academic')
    fl = {}
    for fn in range(1, floors + 1):
        fl[fn] = Floor.objects.create(building=b, floor_number=fn, name=f'Floor {fn}')
    return b, fl


def _make_node(code, fl, nid, name, ntype, x, floor_no=1):
    b = fl[floor_no].building
    return Node.objects.create(
        node_id=nid, building=b, block='T', name=name, type=ntype,
        floor=fl[floor_no], x=x, y=50.0,
        qr_code=f'CAMPUSNAV|INDOOR|{code}|{floor_no}|{nid}')


def _make_edge(a, b, dist=10.0, movement='walk', edge_id=None):
    Edge.objects.create(from_node=a, to_node=b, distance=dist,
                        movement_type=movement, edge_id=edge_id)
    Edge.objects.create(from_node=b, to_node=a, distance=dist,
                        movement_type=movement, edge_id=(edge_id + ':R') if edge_id else None)


class ExplicitIndoorImporterTests(TestCase):
    def test_nodes_edges_upsert_and_deactivate(self):
        from navigation.importer import indoor_importer as ii
        b, fl = _make_indoor_building('IMP', floors=1)
        nodes = [
            {'node_id': 'I_ENT', 'floor': '1', 'name': 'Entrance', 'type': 'entrance',
             'x': '10', 'y': '50', 'qr_code': ''},
            {'node_id': 'I_R1', 'floor': '1', 'name': 'Room 1', 'type': 'room',
             'x': '30', 'y': '50', 'qr_code': ''},
        ]
        node_map, c, u = ii.import_indoor_nodes(b, nodes, 'nodes.csv')
        self.assertEqual((c, u), (2, 0))
        self.assertEqual(node_map['I_ENT'].qr_code, 'CAMPUSNAV|INDOOR|IMP|1|I_ENT')
        count, deact = ii.import_indoor_edges(b, node_map, [
            {'edge_id': 'IE1', 'from_node': 'I_ENT', 'to_node': 'I_R1',
             'distance_m': '', 'movement_type': 'walk'}], 'edges.csv')
        self.assertEqual(count, 2)  # bidirectional
        self.assertEqual(deact, 0)
        # Re-import without the edge → deactivated, not deleted
        count, deact = ii.import_indoor_edges(b, node_map, [], 'edges.csv')
        self.assertEqual(count, 0)
        self.assertEqual(deact, 2)
        self.assertEqual(Edge.objects.filter(edge_id='IE1').count(), 1)

    def test_rejects_duplicate_unknown_and_self_loop(self):
        from navigation.importer import indoor_importer as ii
        from navigation.importer.campus_importer import CampusImportError
        b, fl = _make_indoor_building('IMP2', floors=1)
        with self.assertRaises(CampusImportError):
            ii.import_indoor_nodes(b, [
                {'node_id': 'D', 'floor': '1', 'name': 'A', 'type': 'room', 'x': '1', 'y': '1'},
                {'node_id': 'D', 'floor': '1', 'name': 'B', 'type': 'room', 'x': '2', 'y': '2'},
            ], 'nodes.csv')
        with self.assertRaises(CampusImportError):
            ii.import_indoor_nodes(b, [
                {'node_id': 'W', 'floor': '1', 'name': 'W', 'type': 'teleport', 'x': '1', 'y': '1'},
            ], 'nodes.csv')
        node_map, _, _ = ii.import_indoor_nodes(b, [
            {'node_id': 'E1', 'floor': '1', 'name': 'E1', 'type': 'room', 'x': '1', 'y': '1'},
        ], 'nodes.csv')
        with self.assertRaises(CampusImportError):
            ii.import_indoor_edges(b, node_map, [
                {'edge_id': 'X', 'from_node': 'E1', 'to_node': 'GHOST'}], 'edges.csv')
        with self.assertRaises(CampusImportError):
            ii.import_indoor_edges(b, node_map, [
                {'edge_id': 'Y', 'from_node': 'E1', 'to_node': 'E1'}], 'edges.csv')


class MultiBuildingRoutingTests(TestCase):
    def setUp(self):
        self.client = Client()
        # 8th Block: entrance -> corridor -> stair/lift, 2 floors
        b8, f8 = _make_indoor_building('B8', floors=2)
        self.e8 = _make_node('B8', f8, 'E8', 'Main Entrance', 'entrance', 10.0)
        c8 = _make_node('B8', f8, 'C8', 'Corridor', 'corridor', 30.0)
        s81 = _make_node('B8', f8, 'S81', 'Stairs', 'stair', 50.0)
        s82 = _make_node('B8', f8, 'S82', 'Stairs', 'stair', 50.0, floor_no=2)
        self.h8 = _make_node('B8', f8, 'H8', 'Seminar Hall', 'hall', 70.0, floor_no=2)
        _make_edge(self.e8, c8, 20.0, 'walk', 'M_E1')
        _make_edge(c8, s81, 20.0, 'walk', 'M_E2')
        _make_edge(s81, s82, 15.0, 'stairs', 'M_E3')
        _make_edge(s82, self.h8, 20.0, 'walk', 'M_E4')
        # 3rd Block: entrance -> room on floor 1
        b3, f3 = _make_indoor_building('B3', floors=1)
        self.e3 = _make_node('B3', f3, 'E3', 'Main Entrance', 'entrance', 10.0)
        self.r3 = _make_node('B3', f3, 'R3', 'Room 340', 'room', 30.0)
        _make_edge(self.e3, self.r3, 20.0, 'walk', 'M_E5')
        # Outdoor bridge
        self.o1 = OutdoorNode.objects.create(node_id='O_E8', name='8th Entrance',
                                             type='building_entrance', building=b8,
                                             latitude=9.5, longitude=77.6)
        self.o2 = OutdoorNode.objects.create(node_id='O_E3', name='3rd Entrance',
                                             type='building_entrance', building=b3,
                                             latitude=9.5005, longitude=77.6005)
        OutdoorEdge.objects.create(from_node=self.o1, to_node=self.o2, distance_m=100)
        OutdoorEdge.objects.create(from_node=self.o2, to_node=self.o1, distance_m=100)
        BuildingEntrance.objects.create(entrance_id='B8E', building=b8, outdoor_node_id='O_E8',
                                        indoor_node_id='E8')
        BuildingEntrance.objects.create(entrance_id='B3E', building=b3, outdoor_node_id='O_E3',
                                        indoor_node_id='E3')

    def _route(self, fro, to, mode='any'):
        from navigation import navigation_service as ns
        return ns.calculate_unified_route(
            {'type': 'indoor_node', 'node_id': fro},
            {'type': 'room', 'indoor_node_id': to}, mode=mode)

    def test_multi_building_route(self):
        data = self._route('H8', 'R3')
        self.assertEqual(data['routeType'], 'multi_building')
        self.assertEqual([s['type'] for s in data['segments']], ['indoor', 'outdoor', 'indoor'])
        self.assertTrue(any('Exit' in s for s in data['instructions']))
        self.assertTrue(any('Enter' in s for s in data['instructions']))
        self.assertTrue(data['totalDistanceMetres'] > 0)

    def test_same_building_still_indoor(self):
        data = self._route('E8', 'H8')
        self.assertEqual(data['routeType'], 'indoor')
        self.assertEqual(len(data['segments']), 1)

    def test_indoor_to_outdoor(self):
        from navigation import navigation_service as ns
        data = ns.calculate_unified_route(
            {'type': 'indoor_node', 'node_id': 'H8'},
            {'type': 'building', 'id': 'B3', 'building_code': 'B3'})
        self.assertEqual(data['routeType'], 'indoor_to_outdoor')
        self.assertEqual([s['type'] for s in data['segments']], ['indoor', 'outdoor'])

    def test_multi_building_api(self):
        url = (reverse('api-navigation-route')
               + '?from_type=indoor_node&from_id=H8&to_type=room&to_id=R3')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['routeType'], 'multi_building')

    def test_floor_detail_api(self):
        response = self.client.get(reverse('api-building-floor-detail',
                                           kwargs={'code': 'B8', 'floor': '2'}))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('map', data)
        self.assertTrue(any(n['node_id'] == 'H8' for n in data['nodes']))
        self.assertTrue(len(data['edges']) > 0)
        response = self.client.get(reverse('api-building-floor-detail',
                                           kwargs={'code': 'B8', 'floor': '9'}))
        self.assertEqual(response.status_code, 404)
