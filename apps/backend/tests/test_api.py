import os
os.environ["DATABASE_URL"] = "sqlite:///./test_oliva.db"
os.environ["SECRET_KEY"] = "test-secret"

from fastapi.testclient import TestClient
from sqlmodel import SQLModel
from app.database import engine
from app.main import app


def setup_function():
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)


def auth(client: TestClient):
    response = client.post("/api/auth/register", json={"email": "tony@oliva.uy", "name": "Tony", "password": "secreto123"})
    assert response.status_code == 201
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_health():
    with TestClient(app) as client:
        assert client.get("/health").json()["status"] == "ok"


def test_mvp_flow():
    with TestClient(app) as client:
        headers = auth(client)
        created_client = client.post("/api/clients", headers=headers, json={"name": "Marca Demo", "industry": "Retail"})
        assert created_client.status_code == 201
        project = client.post("/api/projects", headers=headers, json={"name": "Lanzamiento", "client_id": created_client.json()["id"], "brief": "Necesitamos crecer", "objective": "Aumentar consideración"})
        assert project.status_code == 201
        project_id = project.json()["id"]
        upload = client.post(f"/api/projects/{project_id}/documents", headers=headers, files={"file": ("investigacion.txt", b"Las personas valoran la confianza.", "text/plain")})
        assert upload.status_code == 201
        result = client.post(f"/api/projects/{project_id}/analyze", headers=headers)
        assert result.status_code == 200
        assert result.json()["status"] == "completed"
        assert result.json()["result"]["strategic_question"]


def test_project_is_private():
    with TestClient(app) as client:
        headers = auth(client)
        assert client.get("/api/projects").status_code == 401
        assert client.get("/api/projects", headers=headers).status_code == 200
