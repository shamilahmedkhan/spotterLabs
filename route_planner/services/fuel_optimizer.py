from dataclasses import dataclass

from route_planner.exceptions import OptimizationError


@dataclass
class FuelStopCandidate:
    station_id: int
    name: str
    city: str
    state: str
    address: str
    latitude: float
    longitude: float
    price: float
    progress_miles: float
    corridor_distance_miles: float
    is_origin_stop: bool = False


def optimize_fuel_stops(
    stops: list[FuelStopCandidate],
    total_distance_miles: float,
    mpg: float,
    max_range_miles: float,
) -> dict:
    if mpg <= 0:
        raise OptimizationError("MPG must be greater than zero.")
    if max_range_miles <= 0:
        raise OptimizationError("Maximum range must be greater than zero.")
    if not stops:
        raise OptimizationError("No fuel stops available for optimization.")

    gallons_capacity = max_range_miles / mpg
    sorted_stops = sorted(stops, key=lambda item: (item.progress_miles, item.price))
    destination = FuelStopCandidate(
        station_id=-1,
        name="Destination",
        city="",
        state="",
        address="",
        latitude=0.0,
        longitude=0.0,
        price=float("inf"),
        progress_miles=total_distance_miles,
        corridor_distance_miles=0.0,
    )
    sequence = sorted_stops + [destination]

    fuel_in_tank = 0.0
    purchases: list[dict] = []

    for index, current in enumerate(sequence[:-1]):
        next_stop = sequence[index + 1]
        if next_stop.progress_miles - current.progress_miles > max_range_miles:
            raise OptimizationError("Route contains a segment longer than the vehicle range.")

        cheaper_index = None
        farthest_reachable_index = index + 1
        for scan_index in range(index + 1, len(sequence)):
            distance_ahead = sequence[scan_index].progress_miles - current.progress_miles
            if distance_ahead > max_range_miles:
                break
            farthest_reachable_index = scan_index
            if sequence[scan_index].price < current.price:
                cheaper_index = scan_index
                break

        target_index = cheaper_index if cheaper_index is not None else farthest_reachable_index
        target_distance = sequence[target_index].progress_miles - current.progress_miles
        target_gallons = target_distance / mpg
        gallons_to_buy = max(0.0, target_gallons - fuel_in_tank)

        if gallons_to_buy > gallons_capacity + 1e-9:
            raise OptimizationError("Required fuel exceeds tank capacity.")

        if gallons_to_buy > 1e-6:
            purchases.append(
                {
                    "station_id": current.station_id,
                    "name": current.name,
                    "city": current.city,
                    "state": current.state,
                    "address": current.address,
                    "latitude": current.latitude,
                    "longitude": current.longitude,
                    "price_per_gallon": round(current.price, 4),
                    "gallons_purchased": round(gallons_to_buy, 3),
                    "purchase_cost": round(gallons_to_buy * current.price, 2),
                    "progress_miles": round(current.progress_miles, 2),
                    "corridor_distance_miles": round(current.corridor_distance_miles, 2),
                    "is_origin_stop": current.is_origin_stop,
                }
            )
            fuel_in_tank += gallons_to_buy

        gallons_used_to_next = (next_stop.progress_miles - current.progress_miles) / mpg
        fuel_in_tank = max(0.0, fuel_in_tank - gallons_used_to_next)

    return {
        "fuel_stops": purchases,
        "total_cost": round(sum(item["purchase_cost"] for item in purchases), 2),
        "total_gallons": round(sum(item["gallons_purchased"] for item in purchases), 3),
    }
