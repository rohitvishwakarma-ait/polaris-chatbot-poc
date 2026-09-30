import json
import random

import redis


REDIS_HOST = "localhost"
REDIS_PORT = 6379ait


def get_redis_connection() -> redis.Redis:
    return redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        decode_responses=True,
    )


def print_key_counts(r: redis.Redis, title: str) -> None:
    print(title)

    for pattern in [
        "machine:*",
        "production:*",
        "shift:*",
        "dashboard:*",
    ]:
        print(f"  {pattern}: {len(r.keys(pattern))} keys")


def main() -> None:
    r = get_redis_connection()

    # Verify Redis connection
    r.ping()
    print(f"Connected to Redis at {REDIS_HOST}:{REDIS_PORT}")
    print()

    # ---------------------------------------------------------
    # Current Redis key counts
    # ---------------------------------------------------------
    print_key_counts(r, "Current Redis key counts:")
    print()

    # ---------------------------------------------------------
    # Machine: Add M06-M10
    # ---------------------------------------------------------
    new_machines = {
        "machine:M06": {
            "machine_id": "M06",
            "status": "Running",
            "current_production": 6200,
            "product_code": "GB500",
            "shift": "Afternoon",
            "temperature": 191,
            "pressure": 8,
            "speed": 138,
            "defects": 1,
        },
        "machine:M07": {
            "machine_id": "M07",
            "status": "Running",
            "current_production": 9100,
            "product_code": "GB250",
            "shift": "Night",
            "temperature": 197,
            "pressure": 9,
            "speed": 155,
            "defects": 4,
        },
        "machine:M08": {
            "machine_id": "M08",
            "status": "Idle",
            "current_production": 3300,
            "product_code": "GB330",
            "shift": "Morning",
            "temperature": 178,
            "pressure": 5,
            "speed": 0,
            "defects": 0,
        },
        "machine:M09": {
            "machine_id": "M09",
            "status": "Maintenance",
            "current_production": 0,
            "product_code": "GB1000",
            "shift": "Afternoon",
            "temperature": 22,
            "pressure": 0,
            "speed": 0,
            "defects": 0,
        },
        "machine:M10": {
            "machine_id": "M10",
            "status": "Running",
            "current_production": 11400,
            "product_code": "GB750",
            "shift": "Night",
            "temperature": 204,
            "pressure": 10,
            "speed": 142,
            "defects": 2,
        },
    }

    for key, value in new_machines.items():
        r.set(key, json.dumps(value))

    # Update existing machines with fresh values
    existing_machines = {
        "machine:M01": {
            "machine_id": "M01",
            "status": "Running",
            "current_production": 14200,
            "product_code": "GB500",
            "shift": "Morning",
            "temperature": 198,
            "pressure": 9,
            "speed": 147,
            "defects": 3,
        },
        "machine:M02": {
            "machine_id": "M02",
            "status": "Running",
            "current_production": 8900,
            "product_code": "GB750",
            "shift": "Afternoon",
            "temperature": 186,
            "pressure": 7,
            "speed": 131,
            "defects": 1,
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
            "current_production": 16700,
            "product_code": "GB1000",
            "shift": "Morning",
            "temperature": 205,
            "pressure": 11,
            "speed": 129,
            "defects": 2,
        },
        "machine:M05": {
            "machine_id": "M05",
            "status": "Idle",
            "current_production": 5100,
            "product_code": "GB250",
            "shift": "Afternoon",
            "temperature": 180,
            "pressure": 6,
            "speed": 0,
            "defects": 0,
        },
    }

    for key, value in existing_machines.items():
        r.set(key, json.dumps(value))

    print(f"Updated {len(new_machines)} new machine keys")
    print(f"Updated {len(existing_machines)} existing machine keys")
    print(f"Machine keys: {len(r.keys('machine:*'))}")
    print()

    # ---------------------------------------------------------
    # Production: Add 20 more orders
    # ---------------------------------------------------------
    orders = {}

    for i in range(16, 36):
        po = f"PO10{i:02d}"

        progress = random.randint(0, 100)

        quantity = random.choice(
            [
                5000,
                8000,
                10000,
                12000,
                15000,
                18000,
                20000,
                22000,
                25000,
            ]
        )

        product_code = random.choice(
            [
                "GB250",
                "GB330",
                "GB500",
                "GB750",
                "GB1000",
            ]
        )

        orders[f"production:{po}"] = {
            "production_order": po,
            "progress": progress,
            "product_code": product_code,
            "quantity": quantity,
            "completed": int(quantity * progress / 100),
        }

    for key, value in orders.items():
        r.set(key, json.dumps(value))

    print(f"Added {len(orders)} production orders")
    print(f"Production keys: {len(r.keys('production:*'))}")
    print()

    # ---------------------------------------------------------
    # Shift: Add historical shift data
    # ---------------------------------------------------------
    shifts = {
        "shift:current": {
            "shift_name": "Morning",
            "start_time": "06:00",
            "end_time": "14:00",
            "supervisor": "Raj Kumar",
            "machines_active": 5,
            "target_units": 42000,
            "produced_units": 28450,
            "date": "2026-07-08",
        },
        "shift:next": {
            "shift_name": "Afternoon",
            "start_time": "14:00",
            "end_time": "22:00",
            "supervisor": "Priya Singh",
            "machines_active": 4,
            "target_units": 38000,
            "produced_units": 0,
            "date": "2026-07-08",
        },
        "shift:previous": {
            "shift_name": "Night",
            "start_time": "22:00",
            "end_time": "06:00",
            "supervisor": "Amit Shah",
            "machines_active": 3,
            "target_units": 30000,
            "produced_units": 29800,
            "date": "2026-07-07",
        },
        "shift:history:2026-07-07:morning": {
            "shift_name": "Morning",
            "supervisor": "Raj Kumar",
            "machines_active": 5,
            "target_units": 40000,
            "produced_units": 39200,
            "efficiency_pct": 98.0,
            "date": "2026-07-07",
        },
        "shift:history:2026-07-07:afternoon": {
            "shift_name": "Afternoon",
            "supervisor": "Priya Singh",
            "machines_active": 4,
            "target_units": 36000,
            "produced_units": 34500,
            "efficiency_pct": 95.8,
            "date": "2026-07-07",
        },
        "shift:history:2026-07-06:morning": {
            "shift_name": "Morning",
            "supervisor": "Raj Kumar",
            "machines_active": 4,
            "target_units": 38000,
            "produced_units": 37800,
            "efficiency_pct": 99.5,
            "date": "2026-07-06",
        },
        "shift:history:2026-07-06:afternoon": {
            "shift_name": "Afternoon",
            "supervisor": "Priya Singh",
            "machines_active": 5,
            "target_units": 42000,
            "produced_units": 41000,
            "efficiency_pct": 97.6,
            "date": "2026-07-06",
        },
        "shift:history:2026-07-05:morning": {
            "shift_name": "Morning",
            "supervisor": "Amit Shah",
            "machines_active": 5,
            "target_units": 40000,
            "produced_units": 38900,
            "efficiency_pct": 97.3,
            "date": "2026-07-05",
        },
    }

    for key, value in shifts.items():
        r.set(key, json.dumps(value))

    print(f"Added/updated {len(shifts)} shift keys")
    print(f"Shift keys: {len(r.keys('shift:*'))}")
    print()

    # ---------------------------------------------------------
    # Dashboard: Richer KPIs
    # ---------------------------------------------------------
    dashboard = {
        "dashboard:summary": {
            "date": "2026-07-08",
            "total_orders": 85,
            "delivered": 52,
            "processing": 18,
            "pending": 11,
            "cancelled": 4,
            "total_quantity_today": 82450,
            "total_quantity_week": 487200,
            "defect_rate_pct": 1.6,
            "on_time_delivery_pct": 94.2,
        },
        "dashboard:oee": {
            "date": "2026-07-08",
            "machine_availability": 0.87,
            "performance": 0.93,
            "quality": 0.984,
            "oee": 0.795,
            "availability_yesterday": 0.85,
            "performance_yesterday": 0.91,
            "oee_yesterday": 0.768,
        },
        "dashboard:top_products": {
            "GB500": 48500,
            "GB250": 42000,
            "GB330": 38500,
            "GB750": 29200,
            "GB1000": 18900,
        },
        "dashboard:alerts": {
            "active_alerts": 2,
            "alerts": [
                {
                    "machine": "M03",
                    "type": "Maintenance",
                    "severity": "Medium",
                    "message": "Scheduled maintenance in progress",
                },
                {
                    "machine": "M09",
                    "type": "Maintenance",
                    "severity": "Low",
                    "message": "Preventive maintenance check",
                },
            ],
        },
        "dashboard:hourly_output": {
            "date": "2026-07-08",
            "hours": {
                "06": 4200,
                "07": 5100,
                "08": 5300,
                "09": 5000,
                "10": 4800,
                "11": 4050,
            },
        },
    }

    for key, value in dashboard.items():
        r.set(key, json.dumps(value))

    print(f"Added/updated {len(dashboard)} dashboard keys")
    print(f"Dashboard keys: {len(r.keys('dashboard:*'))}")
    print()

    # ---------------------------------------------------------
    # Final verification
    # ---------------------------------------------------------
    print_key_counts(r, "Final Redis key counts:")


if __name__ == "__main__":
    main()