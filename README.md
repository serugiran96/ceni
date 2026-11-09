# Ceni

> Borrador: el README completo (las 9 partes del proyecto final) se escribe el martes 10 de noviembre.

**Ceni** es el sistema de pacientes de los centros de terapia infantil: la terapeuta dicta la sesión y la IA arma la nota, la evolución y el informe para los padres.

Ceni **documenta, no diagnostica**. Todos los pacientes de este repositorio son inventados.

## Cómo correrlo en tu laptop

```bash
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r requirements.txt
cp .env.example .env   # y pega tu OPENAI_API_KEY dentro
.venv/bin/streamlit run streamlit_app.py
```
