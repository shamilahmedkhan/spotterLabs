import math
from dataclasses import dataclass


EARTH_RADIUS_MILES = 3958.7613
MILES_PER_LATITUDE_DEGREE = 69.172


def haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    a = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
    )
    return 2 * EARTH_RADIUS_MILES * math.asin(math.sqrt(a))


def lonlat_to_xy_miles(lon: float, lat: float, ref_lat: float) -> tuple[float, float]:
    x = lon * MILES_PER_LATITUDE_DEGREE * math.cos(math.radians(ref_lat))
    y = lat * MILES_PER_LATITUDE_DEGREE
    return (x, y)


def route_bounding_box(route_points: list[tuple[float, float]]) -> tuple[float, float, float, float]:
    latitudes = [point[0] for point in route_points]
    longitudes = [point[1] for point in route_points]
    return (min(latitudes), max(latitudes), min(longitudes), max(longitudes))


def expand_bounding_box(
    bbox: tuple[float, float, float, float],
    padding_miles: float,
) -> tuple[float, float, float, float]:
    min_lat, max_lat, min_lon, max_lon = bbox
    mid_lat = (min_lat + max_lat) / 2
    lat_padding = padding_miles / MILES_PER_LATITUDE_DEGREE
    lon_padding = padding_miles / max(
        MILES_PER_LATITUDE_DEGREE * math.cos(math.radians(mid_lat)),
        0.0001,
    )
    return (
        min_lat - lat_padding,
        max_lat + lat_padding,
        min_lon - lon_padding,
        max_lon + lon_padding,
    )


@dataclass
class RouteProjection:
    progress_miles: float
    corridor_distance_miles: float


def _perpendicular_distance_miles(
    point: tuple[float, float],
    start: tuple[float, float],
    finish: tuple[float, float],
    ref_lat: float,
) -> float:
    px, py = lonlat_to_xy_miles(point[1], point[0], ref_lat)
    sx, sy = lonlat_to_xy_miles(start[1], start[0], ref_lat)
    fx, fy = lonlat_to_xy_miles(finish[1], finish[0], ref_lat)
    dx = fx - sx
    dy = fy - sy
    length_sq = dx * dx + dy * dy
    if length_sq == 0:
        return math.sqrt((px - sx) ** 2 + (py - sy) ** 2)

    t = max(0.0, min(1.0, ((px - sx) * dx + (py - sy) * dy) / length_sq))
    nearest_x = sx + dx * t
    nearest_y = sy + dy * t
    return math.sqrt((px - nearest_x) ** 2 + (py - nearest_y) ** 2)


def simplify_route(
    route_points: list[tuple[float, float]],
    tolerance_miles: float,
) -> list[tuple[float, float]]:
    if len(route_points) <= 2 or tolerance_miles <= 0:
        return route_points

    ref_lat = sum(point[0] for point in route_points) / len(route_points)

    def rdp(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
        if len(points) <= 2:
            return points

        start = points[0]
        finish = points[-1]
        max_distance = -1.0
        split_index = 0

        for index in range(1, len(points) - 1):
            distance = _perpendicular_distance_miles(
                points[index],
                start,
                finish,
                ref_lat,
            )
            if distance > max_distance:
                max_distance = distance
                split_index = index

        if max_distance <= tolerance_miles:
            return [start, finish]

        left = rdp(points[: split_index + 1])
        right = rdp(points[split_index:])
        return left[:-1] + right

    return rdp(route_points)


def project_point_onto_route(
    point_lat: float,
    point_lon: float,
    route_points: list[tuple[float, float]],
) -> RouteProjection:
    if len(route_points) < 2:
        raise ValueError("Route requires at least two points.")

    cumulative = 0.0
    best_progress = 0.0
    best_distance = float("inf")

    for index in range(len(route_points) - 1):
        start_lat, start_lon = route_points[index]
        end_lat, end_lon = route_points[index + 1]
        ref_lat = (start_lat + end_lat + point_lat) / 3

        ax, ay = lonlat_to_xy_miles(start_lon, start_lat, ref_lat)
        bx, by = lonlat_to_xy_miles(end_lon, end_lat, ref_lat)
        px, py = lonlat_to_xy_miles(point_lon, point_lat, ref_lat)

        dx = bx - ax
        dy = by - ay
        length_sq = dx * dx + dy * dy
        if length_sq == 0:
            segment_distance = haversine_miles(start_lat, start_lon, point_lat, point_lon)
            segment_progress = cumulative
        else:
            t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / length_sq))
            nearest_x = ax + dx * t
            nearest_y = ay + dy * t
            segment_distance = math.sqrt((px - nearest_x) ** 2 + (py - nearest_y) ** 2)
            segment_length = math.sqrt(length_sq)
            segment_progress = cumulative + (segment_length * t)

        if segment_distance < best_distance:
            best_distance = segment_distance
            best_progress = segment_progress

        cumulative += haversine_miles(start_lat, start_lon, end_lat, end_lon)

    return RouteProjection(progress_miles=best_progress, corridor_distance_miles=best_distance)
