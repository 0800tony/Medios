# OLIVA Intelligence

MVP de inteligencia estratégica para `ia.grupooliva.uy`. Permite registrar usuarios, administrar clientes y proyectos, construir una memoria transversal de referencias y generar un diagnóstico inicial con OLIVA Strategy.

## Alcance operativo actual

- autenticación con email y JWT;
- perfil de usuario con actualización de nombre y contraseña;
- clientes y proyectos privados por usuario;
- edición y eliminación protegida de clientes y proyectos;
- brief estratégico guiado, editable, persistente y con indicador de completitud;
- directorio visible de clientes con industria y contexto;
- carga y extracción de texto de PDF, DOCX, TXT y Markdown;
- carga de audio MP3, MP4, M4A, WAV o WEBM, con transcripción automática o manual;
- importación de correos `.eml` y captura manual de mensajes;
- biblioteca de evidencia con enlaces externos y notas de reuniones o entrevistas con el cliente;
- Radar OLIVA para indexar artículos, videos y fotografías que puedan reutilizarse entre proyectos;
- captura automática de título y fuente al guardar enlaces del Radar;
- Biblioteca Cognitiva para casos OLIVA, referencias visuales, criterios de marca, aprendizajes y casos premiados;
- investigación de referencias en fuentes oficiales de Cannes Lions, D&AD, One Club, Clio y Effie;
- análisis visual opcional de fotografías y recuperación automática de señales relevantes para cada brief;
- lectura protegida del contenido público de artículos y metadatos de videos;
- búsqueda híbrida: coincidencia temática local y similitud semántica mediante embeddings cuando hay una API key;
- sugerencias por proyecto con afinidad, motivo y decisión humana de aplicar o descartar;
- contrabrief OLIVA Strategy de 32 apartados, versionado y sujeto a aprobación humana;
- exactamente tres rutas estratégicas diferenciadas y preguntas priorizadas cuando falta información;
- revisión de propuestas creativas contra la estrategia aprobada, con matriz publicitaria de diez criterios;
- análisis con OpenAI Responses API y modo local explícito cuando no hay API key;
- descarga del diagnóstico con manifiesto de fuentes e impresión en PDF;
- interfaz responsive: acceso, home, nuevo proyecto, proyecto y resultado;
- PostgreSQL, Docker Compose y tests de flujo crítico.

## Puesta en marcha

1. Copiar `.env.example` como `.env`.
2. Cambiar `SECRET_KEY`. Agregar `OPENAI_API_KEY` para habilitar el análisis estratégico, visual, semántico y de audio con los modelos configurados.
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
| `GET/PATCH` | `/api/auth/me` | Consultar o actualizar el perfil |
| `GET/POST` | `/api/clients` | Listar/crear clientes |
| `PATCH/DELETE` | `/api/clients/{id}` | Editar/eliminar un cliente sin proyectos |
| `GET/POST` | `/api/projects` | Listar/crear proyectos |
| `GET/PATCH/DELETE` | `/api/projects/{id}` | Consultar, editar o eliminar un proyecto |
| `GET/PUT` | `/api/projects/{id}/brief` | Consultar o editar el brief estratégico completo |
| `GET` | `/api/library` | Consultar la Biblioteca Cognitiva |
| `POST` | `/api/library/links` | Guardar un caso, referencia o aprendizaje enlazado |
| `POST` | `/api/library/files` | Guardar documentos e imágenes institucionales |
| `POST` | `/api/library/festivals` | Investigar casos premiados en fuentes oficiales |
| `GET` | `/api/knowledge` | Buscar la memoria global Radar OLIVA |
| `POST` | `/api/knowledge/links` | Indexar un artículo o video |
| `POST` | `/api/knowledge/photos` | Cargar e indexar una fotografía |
| `POST` | `/api/knowledge/{id}/reindex` | Volver a leer o analizar una señal |
| `GET` | `/api/knowledge/{id}/media` | Consultar una foto protegida |
| `DELETE` | `/api/knowledge/{id}` | Quitar una señal |
| `GET` | `/api/projects/{id}/radar` | Recuperar señales aplicables al proyecto |
| `PATCH` | `/api/projects/{id}/radar/{item_id}` | Aprobar o descartar una sugerencia |
| `POST` | `/api/projects/{id}/documents` | Cargar evidencia |
| `POST` | `/api/projects/{id}/audio` | Cargar y transcribir una grabación |
| `POST` | `/api/projects/{id}/mail-file` | Importar un correo `.eml` |
| `POST` | `/api/projects/{id}/mail` | Guardar un correo pegado manualmente |
| `PATCH` | `/api/projects/{id}/documents/{document_id}/text` | Agregar o corregir una transcripción |
| `GET` | `/api/projects/{id}/documents/{document_id}/media` | Reproducir o descargar una fuente protegida |
| `DELETE` | `/api/projects/{id}/documents/{document_id}` | Quitar un archivo y su texto extraído |
| `POST` | `/api/projects/{id}/evidence` | Agregar referencia o nota del cliente |
| `DELETE` | `/api/projects/{id}/evidence/{evidence_id}` | Quitar evidencia textual |
| `POST` | `/api/projects/{id}/analyze` | Ejecutar OLIVA Strategy |
| `GET` | `/api/projects/{id}/strategy` | Consultar el contrabrief estratégico vigente |
| `PATCH` | `/api/projects/{id}/strategy/approval` | Aprobar o pedir cambios a la estrategia |
| `GET/POST` | `/api/projects/{id}/creative` | Listar o evaluar propuestas creativas |
| `GET` | `/api/projects/{id}/report` | Descargar el diagnóstico y su manifiesto de fuentes |

## Producción

Para `ia.grupooliva.uy`, publicar detrás de un proxy HTTPS y configurar:

- `SECRET_KEY` aleatoria y segura;
- `DATABASE_URL` de PostgreSQL administrado o persistente;
- `NEXT_PUBLIC_API_URL=https://api.ia.grupooliva.uy` (o la ruta pública elegida);
- `CORS_ORIGINS=https://ia.grupooliva.uy`;
- `OPENAI_API_KEY` como secreto del entorno.

Sin una clave de OpenAI, el Radar sigue operativo: lee contenido web público e indexa títulos, contexto y etiquetas. Con la clave, las fotos también reciben una descripción objetiva y las asociaciones combinan coincidencias textuales con similitud semántica usando `text-embedding-3-small`.

Sólo las referencias del Radar aprobadas por una persona entran al siguiente análisis de OLIVA Strategy. Los videos enlazados indexan la información pública y cualquier resumen o transcripción agregada manualmente; extraer automáticamente el audio de plataformas externas queda como una fase posterior.

La transcripción de grabaciones usa `gpt-transcribe` y admite hasta 25 MB. Sin una clave, el archivo igualmente queda protegido dentro del proyecto y la interfaz permite incorporar una transcripción manual.

Las migraciones, el procesamiento asíncrono y el almacenamiento de objetos quedan fuera de este primer sprint y deben incorporarse antes de escalar el servicio.
