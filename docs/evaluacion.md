# Evaluación de modelos de IA

Hecha el 11/11/2026 con `evaluacion/evaluar_modelos.py`, que cualquiera puede volver a correr.
Casos: los 2 guiones de `data/audios_demo/guiones.md` (control de neuropediatría y odontología para pacientes especiales), leídos con las voces en español de la Mac, una por persona.

## 1. Transcripción (voz a texto)

| Modelo | Proveedor | Términos clínicos bien escritos | Error por palabra (WER) | Tiempo por audio | Costo de una consulta de 20 min |
|---|---|---:|---:|---:|---:|
| Whisper large-v3-turbo | Groq | 22 de 22 | 6% | 1.1 s | S/ 0.050 |
| Whisper large-v3 | Groq | 22 de 22 | 5% | 1.7 s | S/ 0.139 |
| whisper-1 | OpenAI | 21 de 22 | 8% | 5.3 s | S/ 0.450 |
| gpt-4o-mini-transcribe | OpenAI | 22 de 22 | 3% | 2.4 s | S/ 0.225 |
| gpt-4o-transcribe | OpenAI | 20 de 22 | 4% | 4.0 s | S/ 0.450 |

El error por palabra cuenta también diferencias de forma (por ejemplo, «1,5» frente a «uno coma cinco»), por eso los términos clínicos son la medida principal.

## 2. Nota de la atención (texto a datos, con salidas estructuradas)

| Modelo | Datos correctos | Datos inventados | Tiempo por nota | Costo por consulta |
|---|---:|---:|---:|---:|
| gpt-4.1-mini | 20 de 20 | 0 | 5.9 s | S/ 0.0106 |
| gpt-4o-mini | 17 de 20 | 0 | 8.4 s | S/ 0.0038 |
| gpt-5-nano | 16 de 20 | 0 | 16.2 s | S/ 0.0043 |
| gpt-5-mini | 18 de 20 | 0 | 35.7 s | S/ 0.0198 |
| gpt-4.1 | 16 de 20 | 0 | 6.8 s | S/ 0.0572 |

Lo que falló en cada modelo:

- **gpt-4.1-mini:** nada
- **gpt-4o-mini:** falta: Terapia de lenguaje; falta: Terapia ocupacional; falta: Diagnóstico de caries (K02)
- **gpt-5-nano:** falta: Terapia de lenguaje; falta: Terapia ocupacional; falta: Pieza: molar; falta: Diagnóstico de caries (K02)
- **gpt-5-mini:** falta: Terapia de lenguaje; falta: Terapia ocupacional
- **gpt-4.1:** falta: Receta: amoxicilina; falta: Amoxicilina 250 mg; falta: Cada 8 horas; falta: Por 5 días

## Límites

- Son 2 casos, con voces sintéticas y sin ruido: sirven para comparar modelos entre sí, no para prometer el acierto en una consulta real. El piloto lo mide con la tasa de corrección de los médicos.
- Cada modelo corrió una vez por caso; los modelos pueden variar entre corridas.
- Precios de lista de noviembre de 2026, de fuentes secundarias; tipo de cambio de S/ 3.75.
