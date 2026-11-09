# Benchmark: historia clínica, citas y notas con IA

Revisión rápida hecha el 9 de noviembre de 2026 con fuentes públicas (webs de las empresas, prensa y comparativas). Varios precios vienen de comparativas hechas por competidores y no coinciden entre sí: son referenciales.

## Las plataformas

| Plataforma | Origen y mercado | Historia clínica | Citas | IA que escucha la consulta | Precio de referencia |
|---|---|---|---|---|---|
| **Doctoralia + Noa Notes** | Docplanner (Polonia/España); en el Perú, más de 13,000 médicos registrados | Sí | Sí: es su producto central (perfil público y reserva online) | Sí: Noa Notes convierte la conversación en un resumen clínico estructurado; en España el audio se borra tras un periodo corto | Noa: 20 a 39 € al mes en España; sin precio público en el Perú |
| **Doctocliq** | Peruana; Perú, México, Ecuador, Colombia | Sí, por especialidad, con recetas | Sí, con recordatorios automáticos | No encontré | Plan gratis hasta 30 pacientes al mes; sede extra US$10 al mes |
| **Medilink** | Chilena; más de 20 países de Latinoamérica | Sí, ficha personalizable con recetas, documentos y consentimientos | Sí: recepción, agenda del médico y vista de toda la clínica; avisos por correo o WhatsApp | Sí: suite de IA con notas clínicas y resumen clínico | No publicado; depende del número de médicos |
| **Abridge** | EE. UU.; grandes sistemas de salud | Se integra con Epic | No | Sí: nota, resumen para el paciente, códigos de facturación y órdenes, todo para revisión y firma del médico | Cotización |
| **Microsoft Dragon Copilot** | EE. UU.; hospitales | Se integra con Epic | No | Sí; graba en español de EE. UU., pero escribe las notas en inglés | Cotización |
| **Nabla** | Francia/EE. UU. | No (se conecta a la del médico) | No | Sí, en 35 idiomas, incluido el español | Plan gratis; Pro cerca de US$119 al mes (dato de terceros) |
| **Heidi Health** | Australia | No (se conecta a la del médico) | No | Sí, más de 110 idiomas y plantillas muy personalizables | Plan gratis; pagados de US$40 a US$150 al mes (fuentes en conflicto) |
| **Freed** | EE. UU.; médicos independientes | No | No | Sí; el plan Premier sugiere códigos CIE-10 y arma cartas e instrucciones para el paciente | US$39, US$79 y US$119 al mes |
| **No hacer nada: papel, Word o Excel** | Lo más común en consultorios chicos | Manual | Cuaderno o WhatsApp | No | "Gratis", pero cuesta horas del médico fuera de horario |

## Lo que se repite en todos (lo mínimo para competir)

1. **Agenda de citas** como puerta de entrada al día del médico: los sistemas latinoamericanos (Doctoralia, Doctocliq, Medilink) parten de ahí.
2. **Historia clínica con recetas**, que se puede imprimir o enviar.
3. **La IA escribe y el médico firma**: todos los asistentes con IA dejan la nota como borrador para revisión y firma (Abridge lo dice explícitamente).
4. **Códigos de diagnóstico** sugeridos (CIE-10 en Freed; códigos de facturación en Abridge).
5. **Privacidad del audio**: el audio no se guarda o se borra rápido (Noa Notes).

## Lo que nadie resuelve para un neuropediatra en el Perú

- **Los asistentes globales piensan en EE. UU.**: precios en dólares, integración con Epic, y Dragon Copilot escribe en inglés aunque la consulta sea en español.
- **Los sistemas latinoamericanos son generalistas**: la IA es un extra y la ficha no está pensada para el neurodesarrollo (desarrollo psicomotor, terapias, colegio).
- **La receta peruana tiene reglas propias**: la Ley 29459 obliga a recetar con la Denominación Común Internacional (DCI), la forma farmacéutica, la dosis, la duración y la vía de administración. Y el metilfenidato, el medicamento más usado en TDAH, es un psicotrópico de la lista IIIA, así que se receta en el recetario especial de DIGEMID y no en una receta común.
- **La historia clínica debe ir firmada** por el profesional, con firma manuscrita o digital (Ley 30024 y NTS 139-MINSA/2018).

## Qué toma Ceni de este benchmark (agregado al MVP)

| Funcionalidad | Por qué | Inspirada en |
|---|---|---|
| Agenda del día y nuevas citas; "Atender" abre la ficha y la cita queda como atendida | Es la puerta de entrada del médico en todos los sistemas de la región | Doctoralia, Doctocliq, Medilink |
| Próximo control agendado desde la misma atención | Cierra el ciclo: lo que el médico dice ("control en 2 meses") se vuelve una cita | Propia |
| Diagnósticos con código CIE-10 (catálogo de neurodesarrollo) | Lo piden los seguros y los reportes; los asistentes líderes ya lo sugieren | Freed, Abridge |
| Receta según la ley peruana (DCI, forma farmacéutica, vía) | La receta tiene que servir en una farmacia del Perú | Ley 29459 |
| Alertas en la receta: psicotrópicos que requieren recetario especial y alergias registradas | Seguridad del paciente y cumplimiento DIGEMID | D.S. 023-2001-SA; práctica de los sistemas de historia clínica |
| "Firmar y guardar": queda quién firmó y cuándo, y cuándo autorizó la familia la grabación | La IA propone, el médico firma | Abridge; Ley 30024; NTS 139 |
| El audio no se guarda, solo la transcripción | Datos de salud de menores | Noa Notes |
| Buscador de pacientes | Básico cuando hay decenas de pacientes | Todos |

**Para después del MVP:** recordatorios por WhatsApp, reserva en línea, resumen o instrucciones para la familia, firma digital con certificado, facturación electrónica (SUNAT), conexión con el gestor de citas del centro e interoperabilidad con el Registro Nacional de Historias Clínicas Electrónicas (RENHICE).

## Fuentes

- Doctoralia y Noa Notes: [Microsoft News (2025)](https://news.microsoft.com/es-es/2025/05/19/doctoralia-optimiza-la-gestion-sanitaria-con-noa-su-asistente-impulsado-por-la-ia-de-microsoft/), [folleto de Noa Notes (Doctoralia España)](https://pro.doctoralia.es/hubfs/es-lg-noa-notes-for-clinics-and-hospitals-2025-brochure.pdf), [precios de Doctoralia Pro (Pabau)](https://pabau.com/es/blog/precios-de-doctoralia-pro/), [Gestión: planes de Doctoralia en el Perú](https://gestion.pe/economia/empresas/los-planes-de-doctoralia-para-crecer-200-hacia-2025-alianzas-y-la-mirada-en-provincias-empresas-telemedicina-medicos-salud-privada-noticia/)
- Doctocliq: [Andina](https://andina.pe/agencia/noticia-peruanos-desarrollan-software-contribuye-a-mejorar-gestion-consultorios-medicos-909865.aspx), [precios (Pabau)](https://pabau.com/es/blog/precios-de-doctocliq/), [Infomercado](https://infomercado.pe/doctocliq-el-software-creado-por-tres-peruanos-ahora-esta-presente-en-12-paises-290922-cch/)
- Medilink: [precios (Pabau)](https://pabau.com/es/blog/precios-de-medilink/), [reseña (Medesk)](https://www.medesk.net/es/blog/medilink-review/)
- Abridge: [nota de prensa](https://www.abridge.com/press-release/patient-centered-clinician-intelligence-platform-keynote), [CHCF](https://www.chcf.org/investment/abridge/)
- Dragon Copilot: [soporte de Microsoft: grabar en español](https://support.microsoft.com/en-US/dragon-copilot/nurses/record-conversations-in-spanish), [página del producto](https://www.microsoft.com/en-ca/health-solutions/clinical-workflow/dragon-copilot)
- Nabla: [35 idiomas](https://nabla.com/press-release/nabla-now-supports-35-languages-to-advance-culturally-responsive-care), [precios (eesel)](https://www.eesel.ai/blog/nabla-ai-pricing)
- Heidi Health: [reseña 2026 (Commure, competidor)](https://www.commure.com/blog-scribe/heidi-health-review), [reseña 2026 (VeroScribe)](https://www.veroscribe.com/blog/heidi-health-review-2026)
- Freed: [página de precios](https://getfreed.ai/pricing)
- Receta en el Perú: [DIGEMID, Comunicado 007-2024 (Ley 29459 y receta electrónica)](https://www.digemid.minsa.gob.pe/Archivos/Comunicados/2024/COM_007-2024.pdf), [metilfenidato en la lista IIIA (PromPerú, DIGEMID)](https://repositorio.promperu.gob.pe/bitstreams/f2abfaf0-b58f-413e-86a1-30684873836b/download), [RM 1105-2002: formato de receta especial](https://cdn.www.gob.pe/uploads/document/file/283009/resolucion-ministerial-n-1105-2002-sa-dm.pdf)
- Historia clínica en el Perú: [NTS 139-MINSA/2018 (El Peruano)](https://busquedas.elperuano.pe/dispositivo/NL/1626125-1), [Ley 30024](https://www.congreso.gob.pe/Docs/DGP/DIDP/files/ley_30024.pdf)
