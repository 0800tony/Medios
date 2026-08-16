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
from app.config import Settings
from app.intelligence import model_for_agent


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


def test_agent_model_routing():
    settings = Settings(openai_strategy_model="strategy", openai_creative_model="creative", openai_operations_model="operations")
    assert model_for_agent(settings, "strategy") == "strategy"
    assert model_for_agent(settings, "creative_director") == "creative"
    assert model_for_agent(settings, "briefing") == "operations"
    assert model_for_agent(settings, "research") == "operations"
    assert model_for_agent(settings, "learning_curator") == "operations"


def test_mvp_flow():
    with TestClient(app) as client:
        headers = auth(client)
        source_list = client.get("/api/research-sources", headers=headers)
        assert source_list.status_code == 200
        assert any(source["name"] == "Adlatina" for source in source_list.json())
        source = next(source for source in source_list.json() if source["name"] == "Marketing Week")
        assert client.patch(f"/api/research-sources/{source['id']}", headers=headers, json={"active": False}).json()["active"] is False
        custom_source = client.post("/api/research-sources", headers=headers, json={"name": "Fuente de prueba", "url": "https://example.org/insights", "country": "Uruguay", "topic": "consumo", "description": "Prueba", "priority": 2})
        assert custom_source.status_code == 201
        assert client.delete(f"/api/research-sources/{custom_source.json()['id']}", headers=headers).status_code == 204
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
        logo = client.post(f"/api/clients/{created_client.json()['id']}/brand-assets", headers=headers, data={"label": "Logo principal", "palette": "#153F35, #D9FF43"}, files={"file": ("logo.png", b"\x89PNG\r\n\x1a\n", "image/png")})
        assert logo.status_code == 201
        assert logo.json()["palette"] == "#153F35, #D9FF43"
        assert client.get(f"/api/clients/{created_client.json()['id']}/brand-assets", headers=headers).json()[0]["id"] == logo.json()["id"]
        assert client.get(f"/api/clients/{created_client.json()['id']}/brand-assets/{logo.json()['id']}/media", headers=headers).content.startswith(b"\x89PNG")
        task = client.post(f"/api/projects/{project_id}/tasks", headers=headers, json={"title": "Validar punto de venta", "assignee": "Dirección de cuentas", "stage": "medios", "priority": "alta"})
        assert task.status_code == 201
        assert client.patch(f"/api/projects/{project_id}/tasks/{task.json()['id']}", headers=headers, json={"status": "in_progress"}).json()["status"] == "in_progress"
        measurement = client.post(f"/api/projects/{project_id}/measurements", headers=headers, json={"metric": "Rotación semanal", "value": "24", "baseline": "12", "target": "30", "period": "Semana 1", "source": "Distribuidor", "notes": "Piloto inicial"})
        assert measurement.status_code == 201
        assert client.get(f"/api/projects/{project_id}/measurements", headers=headers).json()[0]["metric"] == "Rotación semanal"
        watch = client.post("/api/watches", headers=headers, json={"client_id": created_client.json()["id"], "name": "Competidores de retail", "query": "novedades, campañas y lanzamientos", "kind": "competitor"})
        assert watch.status_code == 201
        assert client.patch(f"/api/watches/{watch.json()['id']}", headers=headers, json={"active": False}).json()["active"] is False
        assert client.get("/api/governance", headers=headers).status_code == 200
        assert client.delete(f"/api/clients/{created_client.json()['id']}", headers=headers).status_code == 409
        brief = client.put(f"/api/projects/{project_id}/brief", headers=headers, json={"data": {"request": "Crecer con evidencia", "business_context": "Mercado competitivo", "product": "Servicio", "business_goal": "Crecer", "commercial_goal": "Generar oportunidades", "communication_goal": "Aumentar confianza", "audience": "Personas decisoras", "competitors": "Alternativas regionales", "proof": "Trayectoria", "restrictions": "Presupuesto acotado", "territory": "Uruguay e Interior", "deadline": "Tres meses"}})
        assert brief.status_code == 200
        assert brief.json()["completeness"] == 100
        page = {"title": "Confianza en retail", "source": "Radar Demo", "description": "Señales que construyen confianza", "text": "La exhibición transparente aumenta la consideración.", "final_url": "https://example.com/radar"}
        with patch("app.main.read_link", return_value=page):
            radar_link = client.post("/api/knowledge/links", headers=headers, json={"kind": "article", "title": "", "url": "https://example.com/radar", "source": "", "notes": "La consideracion crece con señales de confianza.", "tags": "consideracion confianza"})
        assert radar_link.status_code == 201
        assert radar_link.json()["index_status"] == "indexed"
        radar_id = radar_link.json()["id"]
        radar_photo = client.post("/api/knowledge/photos", headers=headers, data={"title": "Vidriera de referencia", "notes": "Diseño de retail", "tags": "retail vidriera"}, files={"file": ("vidriera.png", b"\x89PNG\r\n\x1a\n", "image/png")})
        assert radar_photo.status_code == 201
        assert radar_photo.json()["index_status"] == "indexed"
        assert "Indexada con" in radar_photo.json()["ai_observations"]
        radar_photo_id = radar_photo.json()["id"]
        assert client.get(f"/api/knowledge/{radar_photo_id}/media", headers=headers).content.startswith(b"\x89PNG")
        assert radar_link.json()["title"] == "Confianza en retail"
        assert client.get("/api/knowledge?" + "q=confianza", headers=headers).json()[0]["title"] == "Confianza en retail"
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
        with patch("app.main.settings.openai_api_key", "test-key"), patch("app.main.project_web_research", return_value=("El precio requiere contraste con consumidores.", [{"title": "Estudio de mercado", "url": "https://example.com/estudio"}], "modelo de prueba")):
            research = client.post(f"/api/projects/{project_id}/research", headers=headers, json={"query": "Precio y consumo de la categoría"})
        assert research.status_code == 200
        assert research.json()["added_sources"] == 1
        assert research.json()["sources"][0]["url"] == "https://example.com/estudio"
        research_id = next(item["id"] for item in client.get(f"/api/projects/{project_id}", headers=headers).json()["evidence_items"] if item["url"] == "https://example.com/estudio")
        with patch("app.main.read_link", return_value=page):
            library = client.post("/api/library/links", headers=headers, json={"kind": "internal_case", "url": "https://example.com/caso", "description": "Caso exitoso para retail", "results": "Crecimiento", "client_id": created_client.json()["id"]})
        assert library.status_code == 201
        suggestions = client.get(f"/api/projects/{project_id}/library-suggestions", headers=headers)
        assert suggestions.status_code == 200
        assert suggestions.json()[0]["id"] == library.json()["id"]
        note_id = next(item["id"] for item in note.json()["evidence_items"] if item["kind"] == "client_note")
        result = client.post(f"/api/projects/{project_id}/analyze", headers=headers)
        assert result.status_code == 200
        assert result.json()["status"] == "completed"
        assert result.json()["result"]["strategic_question"]
        dossier = client.get(f"/api/projects/{project_id}/strategy", headers=headers)
        assert dossier.status_code == 200
        assert len(dossier.json()["sections"]) == 36
        assert dossier.json()["sections"]["ruta_4"]["nombre"] == "Actualizar el legado para habilitar el presente"
        critical_gaps = dossier.json()["sections"]["que_no_sabemos"]
        assert len(critical_gaps) >= 3
        assert {"vacio", "por_que_importa", "pregunta", "evidencia_necesaria"}.issubset(critical_gaps[0])
        assert dossier.json()["sections"]["proxima_decision"]["resolver_primero"]
        needs_route = client.patch(f"/api/projects/{project_id}/strategy/approval", headers=headers, json={"status": "approved", "notes": "Aprobada por dirección"})
        assert needs_route.status_code == 409
        decision = client.put(f"/api/projects/{project_id}/strategy/decision", headers=headers, json={"route_key": "ruta_3", "rationale": "Primero hay que reducir la fricción comercial antes de ampliar la comunicación.", "launch_plan": "Pilotear la propuesta en dos plazas, medir rotación y ajustar antes de escalar."})
        assert decision.status_code == 200
        assert decision.json()["route_key"] == "ruta_3"
        assert client.get(f"/api/projects/{project_id}/strategy", headers=headers).json()["approval_status"] == "approved"
        assert client.post(f"/api/projects/{project_id}/strategy/expand-routes", headers=headers).json()["sections"]["ruta_7"]["nombre"] == "Redefinir el valor para ganar elección"
        assert client.get(f"/api/projects/{project_id}", headers=headers).json()["workflow_stage"] == "ruta_seleccionada"
        approval = client.patch(f"/api/projects/{project_id}/strategy/approval", headers=headers, json={"status": "approved", "notes": "Aprobada por dirección"})
        assert approval.json()["approval_status"] == "approved"
        concept = client.post(f"/api/projects/{project_id}/creative-concepts/generate", headers=headers, json={"instruction": "Priorizar activación de bajo presupuesto"})
        assert concept.status_code == 201
        assert len(concept.json()["content"]["territorios"]) == 3
        selected_concept = client.patch(f"/api/projects/{project_id}/creative-concepts/{concept.json()['id']}", headers=headers, json={"content": concept.json()["content"], "status": "selected"})
        assert selected_concept.status_code == 200
        assert client.get(f"/api/projects/{project_id}", headers=headers).json()["workflow_stage"] == "plan_de_campana"
        plans = client.get(f"/api/projects/{project_id}/creative-plans", headers=headers)
        assert plans.status_code == 200
        assert len(plans.json()) == 1
        assert plans.json()[0]["content"]["piezas_creativas"]
        assert plans.json()[0]["content"]["soportes_de_medios"]
        approved_plan = client.patch(f"/api/projects/{project_id}/creative-plans/{plans.json()[0]['id']}", headers=headers, json={"content": plans.json()[0]["content"], "status": "approved"})
        assert approved_plan.status_code == 200
        assert approved_plan.json()["content"]["creative_version"] == 2
        assert len(approved_plan.json()["content"]["propuestas_de_produccion"]) >= 3
        assert "guion" in approved_plan.json()["content"]["propuestas_de_produccion"][0]
        assert len(approved_plan.json()["content"]["mesa_de_agentes"]) >= 5
        assert len(approved_plan.json()["content"]["bocetos_visuales"]) >= 1
        assert approved_plan.json()["content"]["criterio_creativo"]["principios"]
        edited_plan = approved_plan.json()["content"]
        edited_plan["propuestas_de_produccion"][0]["guion"] = "Guion escrito y aprobado por el equipo."
        preserved = client.patch(f"/api/projects/{project_id}/creative-plans/{plans.json()[0]['id']}", headers=headers, json={"content": edited_plan, "status": "approved"})
        assert preserved.status_code == 200
        assert preserved.json()["content"]["propuestas_de_produccion"][0]["guion"] == "Guion escrito y aprobado por el equipo."
        edited_concept = selected_concept.json()["content"]
        edited_concept["territorios"][0]["nombre"] = "Nombre elegido por el equipo"
        assert client.patch(f"/api/projects/{project_id}/creative-concepts/{concept.json()['id']}", headers=headers, json={"content": edited_concept, "status": "selected"}).status_code == 200
        assert client.get(f"/api/projects/{project_id}/creative-plans", headers=headers).json()[0]["content"]["propuestas_de_produccion"][0]["guion"] == "Guion escrito y aprobado por el equipo."
        visual = client.post(f"/api/projects/{project_id}/creative-plans/{plans.json()[0]['id']}/visuals/generate", headers=headers, json={"title": "Kiosco de recreo", "focus": "Visualizar una pausa cotidiana en el punto de venta."})
        assert visual.status_code == 503
        assert "No se generó ningún boceto" in visual.json()["detail"]
        assert client.get(f"/api/projects/{project_id}", headers=headers).json()["workflow_stage"] == "produccion_creativa"
        contribution = client.post(f"/api/projects/{project_id}/creative-notes", headers=headers, json={"kind": "idea", "author": "Equipo", "content": "Llevar la prueba de producto al momento de compra."})
        assert contribution.status_code == 201
        assert client.patch(f"/api/projects/{project_id}/creative-notes/{contribution.json()['id']}", headers=headers, json={"status": "applied"}).json()["status"] == "applied"
        table = client.post(f"/api/projects/{project_id}/creative-table", headers=headers, json={"question": "¿Cómo hacemos más propia la pieza madre?"})
        assert table.status_code == 201
        assert len(table.json()["output"]["intervenciones"]) == 4
        package = client.get(f"/api/projects/{project_id}/creative-plans/{plans.json()[0]['id']}/production-package", headers=headers)
        assert package.status_code == 200
        assert package.json()["deliverables"]
        creative = client.post(f"/api/projects/{project_id}/creative", headers=headers, data={"name": "Propuesta A", "medium": "Gráfica", "rationale": "Construye confianza"}, files={"file": ("pieza.txt", b"Titular y llamada a la accion", "text/plain")})
        assert creative.status_code == 201
        assert creative.json()["verdict"] == "revisar"
        assert "ruta 3" in creative.json()["evaluation"].lower()
        annotation = client.post(f"/api/projects/{project_id}/creative/{creative.json()['id']}/annotations", headers=headers, json={"author": "Director creativo", "comment": "Revisar jerarquía de marca antes de producir.", "x": 45, "y": 30})
        assert annotation.status_code == 201
        assert client.patch(f"/api/projects/{project_id}/creative/{creative.json()['id']}/annotations/{annotation.json()['id']}", headers=headers, json={"status": "resolved"}).json()["status"] == "resolved"
        assert library.json()["title"] == "Confianza en retail"
        assert len(client.get("/api/library?kind=internal_case", headers=headers).json()) == 1
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
        assert client.delete(f"/api/projects/{project_id}/evidence/{research_id}", headers=headers).status_code == 204
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


def test_completed_approximations_do_not_reappear_and_route_survives_new_version():
    with TestClient(app) as client:
        headers = auth(client)
        created_client = client.post("/api/clients", headers=headers, json={"name": "Alfajores Demo", "industry": "Alimentos"}).json()
        project = client.post("/api/projects", headers=headers, json={"name": "Flor de Panzada", "client_id": created_client["id"], "brief": "Lanzamiento de nueva marca", "objective": "Construir elección cotidiana"}).json()
        project_id = project["id"]
        brief_data = {
            "request": "Lanzar una marca nueva de alfajores con un precio superior al industrial.", "product": "Alfajor artesanal individual", "commercial_goal": "Crecer con distribución regional", "audience": "Adolescentes y jóvenes", "motivations": "Compra cotidiana en recreo y merienda", "positioning": "Alfajor joven del litoral", "competitors": "Industriales y artesanales", "brand_architecture": "La nueva marca es independiente; El Nogal solo respalda su origen.", "consumer_behavior_evidence": "Comercios observan compra en recreo, viaje y merienda.", "price_value_evidence": "El industrial vale 650-800 y la propuesta 1000; se probará en puntos iniciales.", "capacity_distribution_evidence": "La fábrica tiene turnos ociosos y capacidad hasta 250.000 unidades; falta ampliar logística.", "audience_priority_evidence": "Niños y adolescentes son la primera audiencia por envase, precio y ocasión.", "competitive_product_evidence": "El envase compite bien; la diferencia de precio debe aprenderse en el piloto.",
        }
        assert client.put(f"/api/projects/{project_id}/brief", headers=headers, json={"data": brief_data}).status_code == 200
        first = client.post(f"/api/projects/{project_id}/analyze", headers=headers)
        assert first.status_code == 200
        dossier = client.get(f"/api/projects/{project_id}/strategy", headers=headers).json()
        assert dossier["sections"]["que_no_sabemos"] == []
        saved = client.put(f"/api/projects/{project_id}/strategy/decision", headers=headers, json={"route_key": "ruta_1", "rationale": "Reencuadrar el artesanal como elección cotidiana.", "launch_plan": "Pilotear en kioscos de Concordia y medir rotación."})
        assert saved.status_code == 200
        assert client.post(f"/api/projects/{project_id}/analyze", headers=headers).status_code == 200
        current = client.get(f"/api/projects/{project_id}/strategy/decision", headers=headers)
        assert current.status_code == 200
        assert current.json()["route_key"] == "ruta_1"
        assert current.json()["rationale"] == "Reencuadrar el artesanal como elección cotidiana."


def test_memory_learning_agents_and_approvals():
    with TestClient(app) as client:
        headers = auth(client)
        created_client = client.post("/api/clients", headers=headers, json={"name": "Cliente con memoria", "industry": "Alimentos"}).json()
        project = client.post("/api/projects", headers=headers, json={"name": "Proyecto integrado", "client_id": created_client["id"], "brief": "Analizar lanzamiento", "objective": "Mejorar la elección", "territory": "Uruguay", "group_company": "Oliva Publicidad"})
        assert project.status_code == 201
        project_id = project.json()["id"]
        assert project.json()["workflow_stage"] == "ingreso"
        memory = client.get(f"/api/clients/{created_client['id']}/memory", headers=headers)
        assert memory.status_code == 200
        saved_memory = client.put(f"/api/clients/{created_client['id']}/memory", headers=headers, json={"data": {"tone": "Cercano y preciso", "rejected_patterns": "No usar estereotipos"}})
        assert saved_memory.status_code == 200
        assert saved_memory.json()["data"]["tone"] == "Cercano y preciso"
        foundations = client.get("/api/foundations", headers=headers)
        assert foundations.status_code == 200
        assert any(item["author"] == "Donella Meadows" for item in foundations.json()["references"])
        assert any(item["id"] == "desachate" for item in foundations.json()["festivals"])
        lenses = foundations.json()["creative_lenses"]
        assert any("Joan Costa" in item["names"] for item in lenses)
        assert any("Gastón Bigio" in item["names"] for item in lenses)
        assert any("Claudio Invernizzi" in item["names"] for item in lenses)
        run = client.post(f"/api/projects/{project_id}/agents/run", headers=headers, json={"agent_key": "briefing", "instruction": "Ordenar el pedido"})
        assert run.status_code == 201
        assert run.json()["output"]["tipo"] == "normalización"
        approval = client.get("/api/approvals", headers=headers).json()[0]
        resolved = client.patch(f"/api/approvals/{approval['id']}", headers=headers, json={"status": "approved", "notes": "Correcto"})
        assert resolved.status_code == 200
        assert resolved.json()["status"] == "approved"
        learning = client.post("/api/learning", headers=headers, json={"project_id": project_id, "client_id": created_client["id"], "title": "La prueba precede a la promesa", "content": "En este proyecto, una prueba visible ayudó a ordenar la propuesta antes de comunicarla.", "source_type": "resultado", "confidence": "situado", "tags": "prueba, lanzamiento"})
        assert learning.status_code == 201
        pending = next(item for item in client.get("/api/approvals", headers=headers).json() if item["kind"] == "learning")
        assert client.patch(f"/api/approvals/{pending['id']}", headers=headers, json={"status": "approved", "notes": "Respaldado"}).status_code == 200
        records = client.get(f"/api/learning?project_id={project_id}&status_filter=approved", headers=headers)
        assert records.status_code == 200
        assert records.json()[0]["title"] == "La prueba precede a la promesa"


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
