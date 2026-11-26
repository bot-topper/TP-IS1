# Plataforma de Preguntas y Respuestas — Taller IS1

![Estado](https://img.shields.io/badge/Estado-En%20Desarrollo-blue?style=flat-square)
![Python](https://img.shields.io/badge/Python-3.12+-3776AB?style=flat-square&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-Web%20%26%20API-000000?style=flat-square&logo=flask&logoColor=white)
![Materia](https://img.shields.io/badge/UNRC-Ingenier%C3%ADa%20de%20Software%20I-success?style=flat-square)

---

## Descripción

Plataforma web de preguntas y respuestas (**Q&A**), desarrollada en el contexto del Taller de la asignatura **Ingeniería de Software I** (UNRC)

El sistema permite a los usuarios publicar consultas organizadas por categorías y etiquetas (`#tags`), responder, comentar, votar aportes según su reputación y aceptar soluciones. Como diferencial principal, integra **Agentes de IA (`AgentIA`)** que actúa como un autor más dentro del foro, capaz de asistir de forma automatizada mediante distintos proveedores de modelos de lenguaje (OpenAI, Gemini o modelos locales).

### Patrones de Diseño y Justificacion
* **Factory Method:**  
  Desacopla la instanciación de las publicaciones (`Question` y `Answer`), permitiendo validar reglas específicas al crearlas (por ejemplo, que solo un humano pueda crear preguntas, mientras que tanto humanos como la IA     pueden generar respuestas) sin acoplar el resto del sistema a los constructores concretos.
* **Strategy:**  
  Permite encapsular e intercambiar distintos proveedores o algoritmos de LLM en tiempo de ejecución sin tener que modificar la lógica interna del agente inteligente.
* **Proxy:**  
  Actúa como intermediario frente al modelo de IA real para controlar el acceso antes de consumir recursos externos: verifica si ya existe una respuesta en caché para preguntas similares y controla cuotas de uso por   usuario.
* **Mediator:**  
  Centraliza la coordinación de notificaciones cuando ocurre un evento relevante (como una nueva respuesta o una solución aceptada), evitando que las clases `Question`, `Answer` y `User` estén  acopladas entre sí para enviarse avisos.
* **Command:**  
  Encapsula cada acción administrativa como un objeto independiente, lo que permite registrar un historial de auditoría de cambios y soportar la operación undo() para revertir acciones de moderación.
---

## Diagrama UML

**Version 1**
![Diagrama de Clases UML](diagrama-UML-1.jpg)

**Version 2**
![Diagrama de Clases UML](diagrama-UML-2.png)

---

## Integrantes

| Integrante | Usuario | DNI |
| :--- | :--- | :--- |
| **Integrante 1** - *Alejo Rossaroli Audisio* | [@t1Alejo](https://github.com/t1Alejo) | 47.666.714 |
| **Integrante 2** - *Florencia Tosolini Paez* | [@QC-fl0r1](https://github.com/QC-fl0r1) | 46.887.645 |
| **Integrante 3** - *Jorge Gabriel Zamudio Villarroel* | [@bot-topper](https://github.com/bot-topper) | 47.570.596 |
| **Integrante 4** - *Gonzalo Mateo Garcia* | [@MG4rc1a](https://github.com/MG4rc1a) | 43.606.495 |
| **Integrante 5** - *Santino Gatti Raggi* | [@GoblinCrimes](https://github.com/GoblinCrimes) | 47.988.332 |

---

Instalación y Ejecución

1. Requisitos e instalación de dependencias
```bash
uv sync
```

2. Variables de entorno
Copia `.env.example` a `.env` y provee una key si deseas usar un proveedor LLM externo (OpenAI o Gemini):
```bash
cp .env.example .env
```

3. Base de datos y migraciones
Aplica las migraciones de Alembic:
```bash
uv run alembic upgrade head
```

4. Levantar servidor de desarrollo
```bash
uv run flask --app myapp run --debug
```
Luego abre `http://127.0.0.1:5000/` en el navegador.

---

Rutas Principales

### Web (HTML / Jinja2)
* `GET /questions/` — Listado de preguntas con filtros por categoría y etiqueta.
* `GET/POST /questions/new` — Crear pregunta (`QuestionCreator`, con respuesta automática si incluye `#ia-help`).
* `GET /questions/<id>` — Detalle del hilo, respuestas, votos, comentarios, suscripción y moderación.
* `GET/POST /questions/<id>/edit`, `POST /questions/<id>/delete` — Editar o eliminar pregunta (autor o `AdminUser`).
* `GET/POST /auth/register`, `GET/POST /auth/login`, `POST /auth/logout` — Registro e inicio de sesión.
* `GET /notifications/` — Notificaciones del usuario autenticado.

API REST (JSON)
* `GET /health` — Estado de la aplicación.
* `GET /api/questions` — Listado JSON (soporta `?category=` y `?tag=`).
* `GET /api/questions/<id>` — Detalle JSON de una pregunta y sus respuestas.
* `POST /api/questions` — Crear pregunta vía JSON (requiere sesión).
* `PATCH /api/questions/<id>`, `DELETE /api/questions/<id>` — Actualizar o eliminar pregunta vía JSON.
* `POST /api/questions/<id>/answers` — Crear respuesta vía JSON (requiere sesión).

---

Lint y Pruebas
```bash
uv run ruff check .
uv run pytest -v
```

