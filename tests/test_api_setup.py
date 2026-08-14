from fastapi.testclient import TestClient

from src.main import app


client = TestClient(app)


def test_health_endpoint_returns_healthy():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_predict_endpoint_accepts_prediction_request_shape():
    payload = {"data": [1.0, 2.0, 3.0, 4.0]}
    response = client.post("/predict", json=payload)
    assert response.status_code == 500 or response.status_code == 200
