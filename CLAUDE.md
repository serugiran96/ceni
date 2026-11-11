# Contexto para Claude Code — Proyecto final "Construye tu startup" (Q-Lab PUCP)

> Pega este archivo en la raíz del repo como `CLAUDE.md` (o pásaselo a Claude Code al inicio) y luego usa el **prompt inicial** del final.

---

## 0. Decisiones tomadas (lunes 9 de noviembre de 2026)

> Estas decisiones reemplazan lo que digan las secciones 3 a 6 sobre terapeutas, notas de sesión, objetivos, evolución e informe para padres.

- **Nombre de la startup:** Ceni.
- **Usuario:** el neuropediatra (solo el médico usa el sistema). Pacientes: niños con TEA, TDAH y otras condiciones del neurodesarrollo.
- **Flujo:** el médico abre la ficha del paciente y graba la consulta completa (con autorización de la familia). Al terminar, Whisper transcribe y el LLM devuelve, con salida estructurada validada con Pydantic: (1) el resumen y la nota de la atención, (2) la receta, solo con lo que el médico indicó, y (3) lo nuevo para la historia clínica, que se añade a la existente sin borrar nada. El médico revisa, corrige y guarda.
- **Ficha del paciente:** datos personales, historia clínica (acumulada, con medicación actual y evolución) y atenciones (historial de todas, con la receta en PDF).
- **Agregado tras el benchmark (`docs/benchmark.md`):** agenda del día (Atender → ficha, cita atendida), próximo control agendado desde la atención, diagnósticos con CIE-10 (catálogo de neurodesarrollo en `ai/esquemas.py`), receta según la Ley 29459 (DCI, forma farmacéutica, vía), alertas de psicotrópicos (metilfenidato, lista IIIA) y de alergias (`backend/reglas.py`), "Firmar y guardar" con quién y cuándo, registro de la autorización de la familia, el audio no se guarda, buscador de pacientes.
- **Campos de la consulta (9 de noviembre, tras revisar el SIHCE del MINSA y la NTS 139):** la nota sigue el formato de consulta externa: motivo y tiempo de enfermedad, relato, funciones biológicas (apetito, sed, sueño, orina, deposiciones, estado de ánimo), funciones vitales y antropometría (peso, talla, perímetro cefálico, T°, FC, FR; el IMC lo calcula el código), examen físico y neurológico, diagnósticos CIE-10 con tipo D/P/R (como el HIS), tratamiento (receta con cantidad) y plan de trabajo (exámenes auxiliares, interconsultas y terapias, indicaciones). La historia clínica incluye inmunizaciones.
- **Diseño (10 de noviembre, versión más viva):** violeta eléctrico #5B47FB con degradado hacia coral, y tonos coral, menta, sol, cielo y rosa; tipografía Bricolage Grotesque (títulos) y Plus Jakarta Sans (texto) en `.streamlit/config.toml`. Barra lateral oscura con el logo en blanco (`assets/logo-blanco.png`). CSS y componentes en `app/estilo.py` (tarjetas `tarjeta-*`, `heroe-*` con degradado y `listo-*` en menta). Para volver a los datos del demo se abre la app con `?reiniciar`.
- **Experiencia del médico (10 de noviembre):** la agenda destaca al siguiente paciente con un resumen previo (última atención, lo que quedó pendiente, medicación y alergias); la ficha muestra ese mismo resumen al lado de la grabadora; con el borrador listo, la grabadora se pliega; al firmar aparece la tarjeta "Atención firmada" con los tiempos reales (cuánto tardó la IA y cuánto tardó el médico en revisar), la receta en PDF y el botón al siguiente paciente. Las pestañas de la ficha usan `on_change="rerun"` para poder abrirlas desde el código.
- **Profesionales (11 de noviembre):** el demo tiene dos: la Dra. Nattaly Rozas (neuropediatría) y el Dr. Juan Carlos Pumayali (odontología para pacientes especiales). Están en "medicos" de `data/semilla.json`. En la barra lateral se elige quién atiende (`st.session_state["medico_id"]`): cada uno ve su agenda (`citas.medico_id`) y firma sus atenciones, y la historia clínica es una sola. El borrador guarda su `medico_id`: con otro profesional se oculta, pero no se borra. Pacientes inventados (4): Fabricio Acurio, Antonella Carpio, Matias Umeres y Estefano Benavides.
- **Acierto de Ceni (11 de noviembre):** cada atención guarda el borrador de la IA (`atenciones.borrador_json`). `backend/acierto.py` lo compara con lo firmado, dato por dato y sin IA: acertado, corregido, borrado (inventado) o agregado (omitido). El resultado se ve en la tarjeta de atención firmada, en cada atención y en la agenda (acierto de los últimos 30 días). El resumen no cuenta.
- **Fuera del MVP:** plan de objetivos, gráfico de evolución, informe para padres, recordatorios por WhatsApp, reserva en línea, firma digital con certificado, facturación SUNAT, RENHICE.
- **Límites:** máximo 10 transcripciones por paciente en 7 días; 20 usos de IA por visitante.
- **API de modelos:** OpenAI. `whisper-1` para transcribir (es Whisper, herramienta del curso) y un modelo de chat con salidas estructuradas (`chat.completions.parse`).

## 1. Quién soy

- **Founder:** Melina Rozas, Digital Product Specialist, con más de 6 años en producto digital (retail, telecom, startups).
- Estudia la Diplomatura de Ciencia de Datos para las Ciencias Sociales y la Gestión Pública (Q-Lab PUCP).
- **Por qué soy la founder indicada:** mi hermana está creando un centro de neurología infantil (3 sedes), y yo estoy definiendo sus sistemas (landing y gestor de citas) con el equipo de desarrollo. Conozco el problema de primera mano y sé hacer producto.
- Programo con apoyo de Claude Code. **Tengo que entender todo el código** (el profesor puede pedirme que explique o cambie una parte). Explícame las decisiones importantes mientras construyes.

## 2. La tarea (resumen del enunciado)

- **Curso:** Diplomatura Q-Lab PUCP. Docente: Alexander Quispe. Individual: una persona, una startup.
- **Entrega del link:** martes 10 de noviembre de 2026, hasta las 11:59 p. m. (issue #204 del repo del curso).
- **Presentación:** miércoles 11 de noviembre, **3 minutos con el software funcionando en vivo** (sin diapositivas, o una sola con el one-liner):
  - 0:00–0:30 problema · 0:30–2:30 demo en vivo de un caso de principio a fin · 2:30–3:00 negocio.
- **Reglas:**
  - Problema real y verificable, de preferencia en Perú o Latinoamérica.
  - **Al menos 2 herramientas del curso dentro del producto** (Claude Code, si solo sirve para programar, no cuenta).
  - Repo **público** en GitHub con todo el código; el backend tiene que poder revisarse.
  - Demo: idealmente una URL pública; como mínimo, que corra en la laptop.
  - **Nada de datos personales reales.** Solo datos sintéticos.
  - Commits en varios días (no un solo commit gigante). Nunca subir claves ni el `.env`.
  - Plan B: un video de 60–90 s del software real.
- **Herramientas del curso disponibles:** scraping y APIs, MCP, Document AI (PaddleOCR), dashboards, mapas (GeoPandas/Folium), raster, LLMs con salidas estructuradas y RAG, Hugging Face / fine-tuning de ModernBERT, agentes con crewAI, despliegue y evaluación, **Whisper (voz a texto)**, **texto a voz**, skills de Claude Code, sitio en GitHub Pages.

### Rúbrica (0–20)

| Criterio | Pts |
|---|---|
| Demo funcionando (URL pública + flujo completo en vivo con datos = 7–8; solo en laptop = 4–6) | 8 |
| Problema y usuario (quién, cuánto le cuesta, cómo lo resuelve hoy, 3 conversaciones) | 3 |
| Solución e insight (qué veo que otros no, why now) | 2 |
| Modelo de negocio (quién paga, precio concreto, costo por usuario) | 2 |
| Herramientas del curso (≥2 dentro del producto, y por qué esas) | 2 |
| Repositorio (público, README completo, commits en varios días, sin claves) | 2 |
| Presentación (clara, dentro de 3 min) | 1 |

### El README debe tener estas 9 partes

1. **One-liner** ("Hacemos X para Y mediante Z").
2. **Founder** (nombre, foto, por qué yo; cómo cubro producto, ingeniería, diseño y ventas con agentes de IA).
3. **Problema** (quién con precisión, cuánto cuesta en horas/soles/errores, cómo lo resuelven hoy, evidencia: notas de 3 conversaciones en `docs/research/`).
4. **Solución e insight.**
5. **Why now.**
6. **Demo** (URL o cómo correrlo, 3 capturas, diagrama de arquitectura, qué modelos/APIs y por qué).
7. **Modelo de negocio** (máximo 3 planes con precio, costo por usuario en tokens/servidor/APIs = margen de contribución).
8. **Herramientas del curso** (cuáles y en qué archivo del repo).
9. **Qué hizo el agente** (qué partes generó Claude Code).

Opcional: TAM/SAM/SOM, competencia (incluye "no hacer nada" y "Excel/Word"), primeros 10/100/1,000 usuarios, plan a 3/6/12 meses, riesgos.

### Estructura sugerida del repo

```
mi-startup/
  README.md
  LICENSE            # MIT
  .env.example       # solo nombres de variables
  .gitignore         # incluye .env
  app/               # Streamlit
  backend/           # si hace falta
  ai/                # prompts, esquemas, scripts de IA
  data/              # datos sintéticos
  docs/              # capturas, diagrama, research/ (3 conversaciones)
  notebooks/
```

## 3. La idea elegida

**One-liner tentativo:**
*"Hacemos el sistema de pacientes de los centros de terapia infantil, donde las terapeutas dictan la sesión y la IA arma la nota, la evolución y el informe para los padres."*

**Nombre de la startup:** por definir (propónme 5 opciones cortas). El centro de mi hermana sería el primer cliente; la startup es otra marca.

**Problema:** las terapeutas de lenguaje, ocupacional y de aprendizaje de los centros de neurología y terapia infantil atienden muchos niños al día. Después de cada sesión escriben la nota de evolución, y cada cierto tiempo un informe para los padres o el colegio. Hoy lo hacen en Word, Excel o un cuaderno, muchas veces fuera de horario. Los padres reciben informes técnicos que no entienden, y la información del niño queda dispersa.

**Por qué es startup (y no un proyecto):** muchos centros tienen el mismo problema; el software hace el trabajo (el costo por cliente nuevo es casi cero); suscripción mensual repetida; puede crecer de Lima al Perú y a Latinoamérica. La estrategia: entrar con una función que ahorra tiempo (dictar la nota) y quedarse como el sistema de pacientes del centro.

**Primer cliente:** el centro de mi hermana (3 sedes).

**Herramientas del curso dentro del producto:**
1. **Whisper** (voz a texto): transcribir el dictado de la sesión.
2. **LLM con salidas estructuradas** (JSON validado con Pydantic): convertir la transcripción en nota clínica estructurada y en informe para padres.
3. (Opcional) **Texto a voz:** versión en audio del informe para los padres.
4. (Opcional) **Dashboard:** evolución del paciente.

**Modelo de negocio (borrador, a afinar):** suscripción por profesional al mes (por ejemplo, S/ 39), con hasta 3 planes (por ejemplo: Terapeuta independiente / Centro / Multisede). Calcular el costo por usuario: minutos de audio transcritos + tokens del LLM + servidor.

**Límites importantes:**
- La app **documenta, no diagnostica**. Decirlo en la app y en el README.
- Datos de salud de menores → **solo pacientes inventados** en el demo y en el repo.

## 4. Alcance del MVP (lo único que tiene que funcionar el miércoles)

**Construir:**
1. **Lista de pacientes:** nombre (inventado), edad, motivo de consulta, especialidad, terapeuta asignada. Con 4–6 pacientes sintéticos precargados, cada uno con algunas sesiones previas para que la evolución se vea.
2. **Ficha del paciente:** datos básicos + historial de sesiones.
3. **Nueva sesión por voz:** grabar desde el navegador (`st.audio_input`) o subir un archivo → transcripción con Whisper → el LLM devuelve una nota estructurada (fecha, especialidad, objetivos trabajados, actividades, logros, dificultades, avance por objetivo en escala simple, tareas para casa, observaciones) → la terapeuta puede editarla → se guarda en la ficha.
4. **Evolución:** gráfico de avance por objetivo a lo largo de las sesiones.
5. **Informe para padres:** un botón que genera un resumen cálido y en lenguaje simple de las últimas sesiones, descargable en PDF (y opcionalmente en audio con texto a voz).

**No construir ahora (va en "qué sigue" del pitch):** agenda y citas, pagos y adelantos (Yape/Plin), portal para padres, multisede, roles y login, integración con el gestor de citas del centro.

**Flujo del demo (2 minutos):** abro la lista → entro a la ficha de un niño y veo su historial → dicto la sesión de hoy → aparece la nota estructurada y la guardo → veo la evolución → genero el informe para la mamá.

## 5. Stack técnico propuesto

- **App:** Streamlit (multipágina o pestañas).
- **Persistencia:** SQLite (o JSON) con datos sintéticos en `data/`. En Streamlit Cloud el disco no es persistente: está bien para el demo, pero los datos semilla se recargan en cada arranque.
- **IA:** por definir según la API que tenga. Recomendación: OpenAI para la transcripción (Whisper) y el LLM, con salida estructurada validada con Pydantic. Alternativa: Anthropic para el LLM + Whisper aparte (API, o `faster-whisper` local si quiero que corra sin internet, con el argumento de confidencialidad).
- **PDF:** `fpdf2` o `reportlab`.
- **Gráficos:** Plotly o Altair.
- **Despliegue:** Streamlit Community Cloud, con la clave en `st.secrets`, nunca en el código. Poner tope de gasto en la API.
- Incluir 2–3 audios de ejemplo (grabados por mí, con casos inventados) en `data/audios_demo/` como respaldo por si falla el micrófono en vivo.

## 6. Evidencia: las 3 conversaciones

Tengo que hablar hoy con 3 usuarios potenciales (mi hermana y dos terapeutas). Guardar las notas en `docs/research/entrevista-1.md`, `-2.md` y `-3.md`. Preguntas guía:

1. ¿Cuántos niños atiendes al día o a la semana?
2. ¿Qué escribes después de cada sesión y dónde (Word, Excel, cuaderno, sistema)?
3. ¿Cuánto tiempo te toma por sesión? ¿Y los informes para padres o colegio?
4. ¿Lo haces dentro o fuera de tu horario?
5. ¿Qué es lo más molesto de ese proceso?
6. ¿Qué te piden los padres que hoy cuesta darles?
7. Si una app te armara la nota a partir de un audio de 1 minuto, ¿la usarías? ¿Qué te preocuparía?
8. ¿Cuánto pagaría el centro (o tú) al mes por algo así?

Mensaje de WhatsApp sugerido:
> "Hola, ¿cómo estás? Estoy haciendo un proyecto para mi diplomatura en la PUCP sobre cómo las terapeutas infantiles registran sus sesiones e informes. ¿Me regalas 10 minutos hoy, por llamada o por audio, para hacerte unas preguntas? Me ayudarías un montón 🙏"

## 7. Cronograma restante

- **Lunes 9 (hoy):** 3 entrevistas · crear el repo público · construir el flujo principal · primeros commits · desplegar en Streamlit Cloud.
- **Martes 10:** que 2 personas lo prueben y arreglar lo que falle · README con las 9 partes · 3 capturas y diagrama · video de respaldo de 60–90 s · ensayo con cronómetro · entregar el link antes de las 11:59 p. m.
- **Miércoles 11:** presentación de 3 minutos.

---

## Prompt inicial para Claude Code

```
Lee CLAUDE.md completo: es el contexto de mi proyecto final y mis decisiones.

Quiero construir el MVP descrito en la sección 4, con el stack de la sección 5,
dentro de la estructura de repo de la sección 2. Antes de escribir código:

1. Pregúntame qué API de modelos voy a usar (OpenAI, Anthropic u otra) y
   ajusta el stack a eso.
2. Propónme 5 nombres cortos para la startup.
3. Muéstrame un plan breve por pasos (máximo 8) y espera mi OK.

Luego construye paso a paso, haciendo un commit con mensaje claro al final de
cada paso, y explicándome en 2–3 líneas qué hace cada archivo importante para
que pueda defender el código. Prioriza que el flujo del demo funcione de
principio a fin antes de pulir el diseño. Usa solo datos sintéticos. Nunca
pongas claves en el código: usa .env local y st.secrets en el despliegue.

Cuando el flujo funcione, ayúdame a desplegarlo en Streamlit Community Cloud
y después a escribir el README con las 9 partes de la sección 2.
```
