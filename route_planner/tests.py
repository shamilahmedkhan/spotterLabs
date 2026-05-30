from django.test import SimpleTestCase

from route_planner.services.fuel_optimizer import FuelStopCandidate, optimize_fuel_stops
from route_planner.services.geo import (
    expand_bounding_box,
    project_point_onto_route,
    route_bounding_box,
    simplify_route,
)


class FuelOptimizerTests(SimpleTestCase):
    def test_optimizer_prefers_cheaper_station_ahead(self):
        stops = [
            FuelStopCandidate(
                station_id=1,
                name="Origin Fuel",
                city="A",
                state="TX",
                address="A",
                latitude=0.0,
                longitude=0.0,
                price=4.0,
                progress_miles=0.0,
                corridor_distance_miles=0.0,
                is_origin_stop=True,
            ),
            FuelStopCandidate(
                station_id=2,
                name="Cheap Fuel",
                city="B",
                state="TX",
                address="B",
                latitude=0.0,
                longitude=0.0,
                price=3.0,
                progress_miles=200.0,
                corridor_distance_miles=0.0,
            ),
            FuelStopCandidate(
                station_id=3,
                name="Expensive Fuel",
                city="C",
                state="TX",
                address="C",
                latitude=0.0,
                longitude=0.0,
                price=4.5,
                progress_miles=350.0,
                corridor_distance_miles=0.0,
            ),
        ]

        result = optimize_fuel_stops(
            stops=stops,
            total_distance_miles=420.0,
            mpg=10.0,
            max_range_miles=500.0,
        )

        self.assertEqual(len(result["fuel_stops"]), 2)
        self.assertEqual(result["fuel_stops"][0]["station_id"], 1)
        self.assertEqual(result["fuel_stops"][0]["gallons_purchased"], 20.0)
        self.assertEqual(result["fuel_stops"][1]["station_id"], 2)


class RouteProjectionTests(SimpleTestCase):
    def test_projection_returns_progress_and_distance(self):
        route = [(32.7767, -96.7970), (32.8130, -96.8300), (32.8500, -96.8600)]
        projection = project_point_onto_route(32.8100, -96.8200, route)

        self.assertGreater(projection.progress_miles, 0.0)
        self.assertLess(projection.corridor_distance_miles, 2.0)

    def test_route_simplification_reduces_points(self):
        route = [
            (32.0000, -96.0000),
            (32.0500, -96.0100),
            (32.1000, -96.0200),
            (32.1500, -96.0300),
            (32.2000, -96.0400),
            (32.2500, -96.0500),
        ]

        simplified = simplify_route(route, tolerance_miles=2.0)

        self.assertLess(len(simplified), len(route))
        self.assertEqual(simplified[0], route[0])
        self.assertEqual(simplified[-1], route[-1])

    def test_bounding_box_expansion_adds_padding(self):
        route = [(32.0, -97.0), (33.0, -96.0)]
        expanded = expand_bounding_box(route_bounding_box(route), padding_miles=30.0)

        self.assertLess(expanded[0], 32.0)
        self.assertGreater(expanded[1], 33.0)
        self.assertLess(expanded[2], -97.0)
        self.assertGreater(expanded[3], -96.0)
