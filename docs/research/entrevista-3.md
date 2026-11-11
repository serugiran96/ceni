# Entrevista 3

- **Fecha:** noviembre de 2026
- **Quién (rol, sin nombre completo):** neuropediatra que trabaja en hospital y en consulta privada
- **Medio:** audio con las respuestas a las preguntas (transcripción completa al final)
- **Consentimiento:** sí. «Puedes usar mis respuestas de forma anónima para tu trabajo, no hay problema.»

## Respuestas

1. **¿Cuántos pacientes atiendes al día o a la semana? ¿Cuánto dura cada consulta?**
   En el hospital, entre 12 y 16 pacientes por turno. En privado, unos 5 o 6, porque las consultas son más largas. Una primera consulta de neuropediatría puede durar 45 minutos o una hora; los controles, de 20 a 30 minutos.

2. **¿Cómo registras la consulta y la historia clínica (papel, Word, un sistema)? ¿Durante o después de la consulta?**
   En el hospital, historia clínica electrónica, «aunque no siempre funciona como uno quisiera». En privado, historias en Word organizadas por paciente. Anota durante la consulta, pero después tiene que ordenar todo.

3. **¿Cuánto tiempo te toma por paciente escribir la historia y la receta?**
   Una primera historia, de 15 a 20 minutos adicionales, sobre todo si hay muchos antecedentes. Las recetas son rápidas, pero un informe médico le puede tomar media hora o más.

4. **¿Lo terminas dentro o fuera de tu horario?**
   Los informes se los piden fuera de la consulta y a veces tiene que hacerlos en casa.

5. **¿Qué es lo más molesto de ese proceso?**
   Volver a escribir toda la información: la historia del desarrollo, los tratamientos y las terapias que le cuentan los padres. «Si estoy escribiendo, no puedo prestarles toda la atención que quisiera.»

6. **¿Qué te piden los padres que hoy cuesta darles (recetas, informes, copias de la historia)?**
   Informes para el colegio, certificados, indicaciones para terapias y resúmenes para otros especialistas. «Es bastante trabajo adicional.»

7. **Si una app grabara la consulta (con permiso de la familia) y te dejara lista la historia y la receta para revisar, ¿la usarías? ¿Qué te preocuparía?**
   Sí, sobre todo para las primeras consultas: que organice los antecedentes, el examen neurológico y la evolución, y le deje un borrador del informe. Tendría que ser muy precisa con los términos médicos, y no quiere que la IA «complete cosas que yo no he dicho». Le preocupa la confidencialidad, porque son menores de edad.

8. **¿Cuánto pagarías tú (o el centro) al mes por algo así?**
   «Si funciona bien y realmente me reduce el tiempo de documentación, probablemente unos 120 o 150 soles al mes.» Antes necesitaría probarla con consultas reales y ver qué tan bien reconoce los términos médicos.

## Cita textual (lo más fuerte que dijo)

> «Si estoy escribiendo, no puedo prestarles toda la atención que quisiera.»

## Qué aprendí / qué cambio en Ceni

- Es el usuario principal de Ceni. Su mayor carga son las **primeras consultas**, de 45 a 60 minutos y con muchos antecedentes, y los **informes**.
- Pide que la IA **no complete lo que no dijo**. En Ceni:
  - es una regla del prompt;
  - los campos que no se mencionaron quedan vacíos;
  - el médico revisa y firma.
  - Ejemplo: en la primera prueba con el guion de Fabricio salió un tiempo de enfermedad que nadie dijo, y se corrigió en el prompt.
- Le preocupa que entienda bien los **términos médicos**. Ceni le pasa a Whisper el vocabulario de cada especialidad (medicamentos y diagnósticos) y usa el catálogo CIE-10.
- **Los informes** para el colegio y otros especialistas son el siguiente paso pedido; hoy están fuera del MVP.

---

## Transcripción completa del audio

> Hola, ¿qué tal? Mira, yo trabajo tanto en hospital como en consulta privada, entonces es un poco diferente en cada lugar. En el hospital puedo ver entre 12 y 16 pacientes por turno, dependiendo de la programación, y en privado veo unos 5 o 6 porque las consultas son bastante más largas.
>
> En neuropediatría una primera consulta puede durar 45 minutos o incluso una hora, porque tenemos que revisar todo el desarrollo del niño, antecedentes, evaluaciones anteriores, tratamientos, conversar con los padres. Los controles son más cortos, unos 20 o 30 minutos.
>
> En el hospital usamos historia clínica electrónica, aunque no siempre funciona como uno quisiera. En privado yo tengo mis historias en Word, organizadas por paciente. Generalmente voy anotando durante la consulta, pero después tengo que ordenar todo.
>
> Y eso sí toma tiempo. Una primera historia me puede tomar 15 o 20 minutos adicionales, especialmente si hay muchos antecedentes. Las recetas son rápidas, pero los informes médicos son otra cosa. A veces me puedo demorar media hora o más haciendo uno.
>
> Lo que más me molesta es la cantidad de información que hay que volver a escribir. Por ejemplo, los padres me cuentan toda la historia del desarrollo, los tratamientos que recibió el niño, las terapias, y después tengo que ordenar toda esa información. Y claro, si estoy escribiendo, no puedo prestarles toda la atención que quisiera.
>
> Muchas familias necesitan informes para el colegio, certificados, indicaciones para terapias o resúmenes para otros especialistas. Y eso es bastante trabajo adicional. A veces me los piden fuera de la consulta y tengo que hacerlos en casa.
>
> La aplicación sí me interesaría, sobre todo para las primeras consultas. Si pudiera organizar automáticamente los antecedentes, el examen neurológico, la evolución y dejarme un borrador del informe, sería bastante útil.
>
> Pero tendría que ser muy precisa. Hay términos médicos que no son fáciles de interpretar y tampoco quisiera que la inteligencia artificial complete cosas que yo no he dicho. Y obviamente está el tema de la confidencialidad, porque estamos hablando de menores de edad.
>
> Sobre cuánto pagaría, si funciona bien y realmente me reduce el tiempo de documentación, probablemente unos 120 o 150 soles al mes. Pero primero necesitaría probarla con consultas reales y ver qué tan bien reconoce los términos médicos.
>
> Sí, puedes usar mis respuestas de forma anónima para tu trabajo, no hay problema.
