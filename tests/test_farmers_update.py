from fastapi.testclient import TestClient
from src.main import app
import random


client = TestClient(app)


def test_create_and_update_farmer():
    # Create a farmer
    payload = {
        "name": f"TestUser{random.randint(1,10000)}",
        "farm_country": "Kenya",
        "farm_state_region": "NA",
        "phone_number": f"+2547{random.randint(10000000,99999999)}",
        "area_of_farmland": 1.5,
        "crop_profiles": [
            {"crop_type": "Maize", "planting_month": "April", "harvest_month": "Aug", "average_yield_tons": 1.2}
        ]
    }

    r = client.post("/farmers", json=payload)
    assert r.status_code == 200
    farmer = r.json()
    fid = farmer["id"] if isinstance(farmer, list) else farmer.get("id")
    assert fid is not None

    # Update farmer - change phone and area
    update_payload = {"phone_number": f"+2547{random.randint(10000000,99999999)}", "area_of_farmland": 2.5}
    r2 = client.put(f"/farmers/{fid}", json=update_payload)
    assert r2.status_code == 200
    updated = r2.json()
    assert float(updated.get("area_of_farmland", 0)) == 2.5
