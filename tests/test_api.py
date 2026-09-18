import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))
sys.path.insert(0, str(BACKEND_DIR.parent))

# Ensure test auth secret key is set
os.environ["AUTH_SECRET_KEY"] = "9f8c6b71e35a4d2f098c1a7e5b3d2c1f4e6a8b0c2d4e6f8a0b2c4d6e8f0a2b4c"

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_auth_flow():
    # Invalid login
    res = client.post("/auth/login", json={"username": "admin", "password": "wrongpassword"})
    assert res.status_code == 401, f"Expected 401, got {res.status_code}"

    # Valid login
    res = client.post("/auth/login", json={"username": "admin", "password": "admin123"})
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    data = res.json()
    assert "token" in data
    token = data["token"]
    assert data["user"]["username"] == "admin"

    # Get /auth/me with token
    res = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.json()["username"] == "admin"

    # Get /auth/me without token
    res = client.get("/auth/me")
    assert res.status_code == 401

    # Logout
    res = client.post("/auth/logout")
    assert res.status_code == 200


def test_tickets_and_admin_flow():
    # 1. Seed sample tickets
    seed_res = client.post("/admin/tickets/seed-samples")
    assert seed_res.status_code == 200
    assert "seeded" in seed_res.json()

    # 2. Get tickets
    tickets_res = client.get("/tickets")
    assert tickets_res.status_code == 200
    tickets = tickets_res.json()
    assert len(tickets) > 0
    ticket_id = tickets[0]["id"]

    # 3. Get stats
    stats_res = client.get("/tickets/stats")
    assert stats_res.status_code == 200
    stats = stats_res.json()
    assert stats["total"] > 0
    assert "categories" in stats

    # 4. Get single ticket
    single_res = client.get(f"/tickets/{ticket_id}")
    assert single_res.status_code == 200
    assert single_res.json()["id"] == ticket_id

    # 5. Patch ticket status
    patch_res = client.patch(f"/tickets/{ticket_id}/status", json={"status": "in_progress"})
    assert patch_res.status_code == 200
    assert patch_res.json()["status"] == "in_progress"

    # 6. Send quote
    quote_res = client.post(
        f"/tickets/{ticket_id}/send-quote",
        json={
            "quote_title": "Pipe Replacement",
            "quote_amount": "$120.00",
            "quote_options": [{"label": "Standard Repair", "price": "$120.00"}],
            "notes": "Estimated 1 hour labor.",
        },
    )
    assert quote_res.status_code == 200
    assert quote_res.json()["quote_status"] == "sent"

    # 7. Approve quote
    approve_res = client.post(
        f"/tickets/{ticket_id}/approve-quote",
        json={"selected_option": "Standard Repair"},
    )
    assert approve_res.status_code == 200
    assert approve_res.json()["quote_status"] == "approved"

    # 8. Team forward
    forward_res = client.post(
        f"/admin/tickets/{ticket_id}/forward-team",
        json={"to_email": "tech@example.com", "body": "Please review this issue."},
    )
    assert forward_res.status_code == 200
    assert forward_res.json()["success"] is True

    # 9. Team resolve and close
    resolve_res = client.post(
        f"/tickets/{ticket_id}/team-resolve-and-close",
        json={
            "resolution_notes": "Pipe replaced and sealed. No leaks detected.",
            "final_bill": "$120.00",
            "technician_name": "Dave Rodriguez",
        },
    )
    assert resolve_res.status_code == 200
    assert resolve_res.json()["status"] == "confirmed_fixed"

    # 10. Confirm ticket
    confirm_res = client.post(f"/tickets/{ticket_id}/confirm")
    assert confirm_res.status_code == 200

    # 11. Delete ticket
    del_res = client.delete(f"/tickets/{ticket_id}")
    assert del_res.status_code == 200
    assert del_res.json()["deleted"] is True


if __name__ == "__main__":
    print("Running test_auth_flow...")
    test_auth_flow()
    print("[OK] Auth flow tests passed")

    print("Running test_tickets_and_admin_flow...")
    test_tickets_and_admin_flow()
    print("[OK] Tickets and Admin flow tests passed")

    print("\n[OK] All API smoke tests passed successfully!")
