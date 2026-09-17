import json

import redis


def main() -> None:
    r = redis.Redis(
        host="localhost",
        port=6379,
        decode_responses=True,
    )

    # Machine status
    machines = {
        "machine:M01": {
            "machine_id": "M01",
            "status": "Running",
            "current_production": 8450,
            "product_code": "GB500",
            "shift": "Morning",
            "temperature": 195,
            "pressure": 8,
            "speed": 145,
            "defects": 2,
        },
        "machine:M02": {
            "machine_id": "M02",
            "status": "Idle",
            "current_production": 4200,
            "product_code": "GB750",
            "shift": "Afternoon",
            "temperature": 180,
            "pressure": 6,
            "speed": 0,
            "defects": 0,
        },
        "machine:M03": {
            "machine_id": "M03",
            "status": "Maintenance",
            "current_production": 0,
            "product_code": "GB330",
            "shift": "Night",
            "temperature": 25,
            "pressure": 0,
            "speed": 0,
            "defects": 0,
        },
        "machine:M04": {
            "machine_id": "M04",
            "status": "Running",
            "current_production": 12300,
            "product_code": "GB1000",
            "shift": "Morning",
            "temperature": 202,
            "pressure": 9,
            "speed": 132,
            "defects": 1,
        },
        "machine:M05": {
            "machine_id": "M05",
            "status": "Running",
            "current_production": 7800,
            "product_code": "GB250",
            "shift": "Afternoon",
            "temperature": 188,
            "pressure": 7,
            "speed": 158,
            "defects": 3,
        },
    }

    for key, value in machines.items():
        r.set(key, json.dumps(value))

    print(f"Set {len(machines)} machine keys")

    # Production progress
    production = {
        "production:PO1001": {
            "production_order": "PO1001",
            "progress": 100,
            "product_code": "GB500",
            "quantity": 12000,
            "completed": 12000,
        },
        "production:PO1002": {
            "production_order": "PO1002",
            "progress": 100,
            "product_code": "GB750",
            "quantity": 8500,
            "completed": 8500,
        },
        "production:PO1008": {
            "production_order": "PO1008",
            "progress": 78,
            "product_code": "GB500",
            "quantity": 10000,
            "completed": 7800,
        },
        "production:PO1013": {
            "production_order": "PO1013",
            "progress": 45,
            "product_code": "GB330",
            "quantity": 15000,
            "completed": 6750,
        },
        "production:PO1015": {
            "production_order": "PO1015",
            "progress": 0,
            "product_code": "GB1000",
            "quantity": 5000,
            "completed": 0,
        },
        "production:PO1016": {
            "production_order": "PO1016",
            "progress": 62,
            "product_code": "GB250",
            "quantity": 20000,
            "completed": 12400,
        },
        "production:PO1017": {
            "production_order": "PO1017",
            "progress": 88,
            "product_code": "GB500",
            "quantity": 9000,
            "completed": 7920,
        },
        "production:PO1018": {
            "production_order": "PO1018",
            "progress": 15,
            "product_code": "GB750",
            "quantity": 6000,
            "completed": 900,
        },
    }

    for key, value in production.items():
        r.set(key, json.dumps(value))

    print(f"Set {len(production)} production keys")

    # Shift information
    shifts = {
        "shift:current": {
            "shift_name": "Morning",
            "start_time": "06:00",
            "end_time": "14:00",
            "supervisor": "Raj Kumar",
            "machines_active": 3,
            "target_units": 25000,
            "produced_units": 18450,
        },
        "shift:next": {
            "shift_name": "Afternoon",
            "start_time": "14:00",
            "end_time": "22:00",
            "supervisor": "Priya Singh",
            "machines_active": 2,
            "target_units": 22000,
            "produced_units": 0,
        },
        "shift:previous": {
            "shift_name": "Night",
            "start_time": "22:00",
            "end_time": "06:00",
            "supervisor": "Amit Shah",
            "machines_active": 2,
            "target_units": 18000,
            "produced_units": 17500,
        },
    }

    for key, value in shifts.items():
        r.set(key, json.dumps(value))

    print(f"Set {len(shifts)} shift keys")

    # Dashboard KPIs
    dashboard = {
        "dashboard:summary": {
            "date": "2026-07-08",
            "total_orders": 35,
            "delivered": 22,
            "processing": 6,
            "pending": 5,
            "cancelled": 2,
            "total_quantity_today": 52450,
            "defect_rate_pct": 1.8,
        },
        "dashboard:oee": {
            "machine_availability": 0.85,
            "performance": 0.92,
            "quality": 0.982,
            "oee": 0.768,
        },
        "dashboard:top_products": {
            "GB500": 28500,
            "GB250": 22000,
            "GB330": 20000,
            "GB750": 14200,
            "GB1000": 9900,
        },
    }

    for key, value in dashboard.items():
        r.set(key, json.dumps(value))

    print(f"Set {len(dashboard)} dashboard keys")

    # Verify
    print()
    print("Redis key counts:")

    for pattern in [
        "machine:*",
        "production:*",
        "shift:*",
        "dashboard:*",
    ]:
        count = len(r.keys(pattern))
        print(f"  {pattern}: {count} keys")


if __name__ == "__main__":
    main()
