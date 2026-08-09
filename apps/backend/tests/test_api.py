import os
from unittest.mock import patch
os.environ["DATABASE_URL"] = "sqlite:///./test_oliva.db"
os.environ["SECRET_KEY"] = "test-secret"

from fastapi.testclient import TestClient
from sqlmodel import SQLModel
from app.database import engine
from app.main import app
from app.link_reader import extract_page
from app.ingestion import extract_email


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
        updated_client = client.patch(f"/api/clients/{created_client.json()['id']}", headers=headers, json={"name": "Marca Demo", "industry": "Retail y servicios", "description": "Opera en Uruguay"})
        assert updated_client.status_code == 200
        assert updated_client.json()["industry"] == "Retail y servicios"
        updated_project = client.patch(f"/api/projects/{project_id}", headers=headers, json={"name": "Lanzamiento regional", "brief": "Necesitamos crecer con evidencia", "objective": "Aumentar consideración"})
        assert updated_project.status_code == 200
        assert updated_project.json()["name"] == "Lanzamiento regional"
        assert client.delete(f"/api/clients/{created_client.json()['id']}", headers=headers).status_code == 409
        page = {"title": "Confianza en retail", "source": "Radar Demo", "description": "Señales que construyen confianza", "text": "La exhibición transparente aumenta la consideración.", "final_url": "https://example.com/radar"}
        with patch("app.main.read_link", return_value=page):
            radar_link = client.post("/api/knowledge/links", headers=headers, json={"kind": "article", "title": "Consideracion y confianza", "url": "https://example.com/radar", "source": "Radar Demo", "notes": "La consideracion crece con señales de confianza.", "tags": "consideracion confianza"})
        assert radar_link.status_code == 201
        assert radar_link.json()["index_status"] == "indexed"
        radar_id = radar_link.json()["id"]
        radar_photo = client.post("/api/knowledge/photos", headers=headers, data={"title": "Vidriera de referencia", "notes": "Diseño de retail", "tags": "retail vidriera"}, files={"file": ("vidriera.png", b"\x89PNG\r\n\x1a\n", "image/png")})
        assert radar_photo.status_code == 201
        assert radar_photo.json()["index_status"] == "manual"
        radar_photo_id = radar_photo.json()["id"]
        assert client.get(f"/api/knowledge/{radar_photo_id}/media", headers=headers).content.startswith(b"\x89PNG")
        assert client.get("/api/knowledge?" + "q=confianza", headers=headers).json()[0]["title"] == "Consideracion y confianza"
        suggestion = client.get(f"/api/projects/{project_id}/radar", headers=headers).json()[0]
        assert suggestion["item"]["id"] == radar_id
        assert suggestion["status"] == "suggested"
        approved = client.patch(f"/api/projects/{project_id}/radar/{radar_id}", headers=headers, json={"status": "approved"})
        assert approved.status_code == 200
        assert approved.json()["status"] == "approved"
        upload = client.post(f"/api/projects/{project_id}/documents", headers=headers, files={"file": ("investigacion.txt", b"Las personas valoran la confianza.", "text/plain")})
        assert upload.status_code == 201
        with patch("app.main.transcribe_audio", return_value="El equipo necesita crecer sin perder la identidad artesanal."):
            audio = client.post(f"/api/projects/{project_id}/audio", headers=headers, data={"context": "Entrevista con gerencia"}, files={"file": ("entrevista.wav", b"RIFF-audio-demo", "audio/wav")})
        assert audio.status_code == 201
        audio_item = next(item for item in audio.json()["documents"] if item["category"] == "audio")
        assert audio_item["processed"] is True
        assert "identidad artesanal" in audio_item["text_excerpt"]
        assert client.get(f"/api/projects/{project_id}/documents/{audio_item['id']}/media", headers=headers).content == b"RIFF-audio-demo"
        raw_mail = b"From: cliente@example.com\nTo: estrategia@oliva.uy\nSubject: Informacion comercial\nContent-Type: text/plain; charset=utf-8\n\nTenemos capacidad ociosa y queremos crecer."
        mail = client.post(f"/api/projects/{project_id}/mail-file", headers=headers, files={"file": ("consulta.eml", raw_mail, "message/rfc822")})
        assert mail.status_code == 201
        mail_item = next(item for item in mail.json()["documents"] if item["category"] == "email")
        assert "capacidad ociosa" in mail_item["text_excerpt"]
        reference = client.post(f"/api/projects/{project_id}/evidence", headers=headers, json={"kind": "reference", "title": "Tendencias de confianza", "url": "https://example.com/articulo", "source": "Medio Demo", "content": "Contexto sectorial relevante."})
        assert reference.status_code == 201
        assert reference.json()["evidence_items"][0]["kind"] == "reference"
        reference_id = reference.json()["evidence_items"][0]["id"]
        note = client.post(f"/api/projects/{project_id}/evidence", headers=headers, json={"kind": "client_note", "title": "Reunion inicial", "source": "Gerencia comercial", "content": "El cliente percibe una brecha de confianza."})
        assert note.status_code == 201
        assert len(note.json()["evidence_items"]) == 2
        note_id = next(item["id"] for item in note.json()["evidence_items"] if item["kind"] == "client_note")
        result = client.post(f"/api/projects/{project_id}/analyze", headers=headers)
        assert result.status_code == 200
        assert result.json()["status"] == "completed"
        assert result.json()["result"]["strategic_question"]
        report = client.get(f"/api/projects/{project_id}/report", headers=headers)
        assert report.status_code == 200
        assert report.headers["content-type"].startswith("text/markdown")
        assert "Marca Demo" in report.text
        assert "investigacion.txt" in report.text
        assert "Radar OLIVA" in report.text
        upload_document = next(item for item in result.json()["documents"] if item["filename"] == "investigacion.txt")
        assert client.delete(f"/api/projects/{project_id}/documents/{upload_document['id']}", headers=headers).status_code == 204
        assert client.get(f"/api/projects/{project_id}/documents/{upload_document['id']}/media", headers=headers).status_code == 404
        assert client.delete(f"/api/projects/{project_id}/evidence/{note_id}", headers=headers).status_code == 204
        assert client.delete(f"/api/projects/{project_id}/evidence/{reference_id}", headers=headers).status_code == 204
        assert client.get(f"/api/projects/{project_id}", headers=headers).json()["evidence_items"] == []
        assert client.delete(f"/api/knowledge/{radar_id}", headers=headers).status_code == 204
        assert client.delete(f"/api/knowledge/{radar_photo_id}", headers=headers).status_code == 204
        assert client.delete(f"/api/projects/{project_id}", headers=headers).status_code == 204
        assert client.get(f"/api/projects/{project_id}", headers=headers).status_code == 404
        assert client.delete(f"/api/clients/{created_client.json()['id']}", headers=headers).status_code == 204


def test_project_is_private():
    with TestClient(app) as client:
        headers = auth(client)
        assert client.get("/api/projects").status_code == 401
        assert client.get("/api/projects", headers=headers).status_code == 200


def test_user_can_update_profile_and_password():
    with TestClient(app) as client:
        headers = auth(client)
        updated = client.patch("/api/auth/me", headers=headers, json={"name": "Antonio Oliva", "current_password": "secreto123", "new_password": "nuevo-secreto-123"})
        assert updated.status_code == 200
        assert updated.json()["name"] == "Antonio Oliva"
        assert client.post("/api/auth/login", json={"email": "tony@oliva.uy", "password": "nuevo-secreto-123"}).status_code == 200


def test_extracts_readable_page_content():
    html = b"""<html><head><title>Retail humano</title><meta property='og:site_name' content='Medio Demo'><meta name='description' content='Una tendencia relevante'></head><body><nav>Ignorar menu</nav><main><h1>Experiencias cercanas</h1><p>Las personas valoran espacios simples.</p></main><script>ignorar()</script></body></html>"""
    page = extract_page(html, "text/html")
    assert page["title"] == "Retail humano"
    assert page["source"] == "Medio Demo"
    assert "espacios simples" in page["text"]
    assert "Ignorar menu" not in page["text"]


def test_extracts_email_headers_and_body():
    raw = b"From: cliente@example.com\nTo: planner@oliva.uy\nSubject: Reunion de lanzamiento\nContent-Type: text/plain; charset=utf-8\n\nLa prioridad es crecer en Argentina."
    text = extract_email(raw)
    assert "ASUNTO: Reunion de lanzamiento" in text
    assert "DE: cliente@example.com" in text
    assert "crecer en Argentina" in text
