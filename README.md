# Ceni

> Borrador: el README completo (las 9 partes del proyecto final) se escribe el martes 10 de noviembre.

**Ceni** es el sistema de pacientes del neuropediatra: graba la consulta y la IA deja lista la historia clínica, el resumen de la atención y la receta para que el médico los revise.

Ceni **documenta: no diagnostica ni receta por su cuenta**. Todos los pacientes de este repositorio son inventados.

## Cómo correrlo en tu laptop

```bash
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r requirements.txt
cp .env.example .env   # y pega tu OPENAI_API_KEY dentro
.venv/bin/streamlit run streamlit_app.py
```
