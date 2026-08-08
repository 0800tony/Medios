# OLIVA Intelligence

MVP de inteligencia estratégica para `ia.grupooliva.uy`. Permite registrar usuarios, administrar clientes y proyectos, cargar evidencia y generar un diagnóstico inicial con OLIVA Strategy.

## Alcance del Sprint 1

- autenticación con email y JWT;
- clientes y proyectos privados por usuario;
- carga y extracción de texto de PDF, DOCX, TXT y Markdown;
- biblioteca de evidencia con enlaces externos y notas de reuniones o entrevistas con el cliente;
- análisis con OpenAI y modo local explícito cuando no hay API key;
- interfaz responsive: acceso, home, nuevo proyecto, proyecto y resultado;
- PostgreSQL, Docker Compose y tests de flujo crítico.

## Puesta en marcha

1. Copiar `.env.example` como `.env`.
2. Cambiar `SECRET_KEY`. Agregar `OPENAI_API_KEY` para habilitar análisis con el modelo configurado.
3. Ejecutar:

```bash
docker compose up --build
```

Frontend: `http://localhost:3000`
API y documentación: `http://localhost:8000/docs`
Salud: `http://localhost:8000/health`

La base y los documentos se guardan en volúmenes Docker. En modo local sin Docker, el backend usa SQLite si no se define `DATABASE_URL`.

## Desarrollo local

Backend:

```bash
cd apps/backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
pytest
```

Frontend:

```bash
cd apps/frontend
npm install
npm run dev
npm run build
```

## API principal

| Método | Ruta | Uso |
|---|---|---|
| `POST` | `/api/auth/register` | Crear cuenta |
| `POST` | `/api/auth/login` | Iniciar sesión |
| `GET/POST` | `/api/clients` | Listar/crear clientes |
| `GET/POST` | `/api/projects` | Listar/crear proyectos |
| `POST` | `/api/projects/{id}/documents` | Cargar evidencia |
| `POST` | `/api/projects/{id}/evidence` | Agregar referencia o nota del cliente |
| `DELETE` | `/api/projects/{id}/evidence/{evidence_id}` | Quitar evidencia textual |
| `POST` | `/api/projects/{id}/analyze` | Ejecutar OLIVA Strategy |

## Producción

Para `ia.grupooliva.uy`, publicar detrás de un proxy HTTPS y configurar:

- `SECRET_KEY` aleatoria y segura;
- `DATABASE_URL` de PostgreSQL administrado o persistente;
- `NEXT_PUBLIC_API_URL=https://api.ia.grupooliva.uy` (o la ruta pública elegida);
- `CORS_ORIGINS=https://ia.grupooliva.uy`;
- `OPENAI_API_KEY` como secreto del entorno.

Las migraciones, el procesamiento asíncrono y el almacenamiento de objetos quedan fuera de este primer sprint y deben incorporarse antes de escalar el servicio.
