from rest_framework.test import APIClient


def test_service_index_points_to_local_api_surfaces():
    response = APIClient().get("/")

    assert response.status_code == 200
    assert response.json() == {
        "service": "tripos-api",
        "product": "TripOS",
        "admin": "/admin/",
        "health": "/api/health/",
    }


def test_health_endpoint_returns_ok():
    response = APIClient().get("/api/health/")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "tripos-api",
        "product": "TripOS",
    }
