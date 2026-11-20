# Reglas de negocio de la Matriz SGR

Fuente: correo «Matriz SGR 4to semestre; puntos a considerar» (Coordinación de Delegaciones, 08-10-2026) y «Descriptor de funciones para los cargos de las Delegaciones» (2026).

| N.º correo | Regla | Implementación | Prueba automática |
|---|---|---|---|
| 1 | Si el usuario es el propio delegado, la actividad no se contabiliza («otra gestión») | Campo «Solicitante = El propio delegado» → 0 puntos (`matriz/reglas.py: calcular_puntaje`) | `test_usuario_delegado_no_suma` |
| 2 | Sin nombre y teléfono del usuario no hay puntuación | Nombre y teléfono vacíos → 0 puntos, con el motivo visible | `test_sin_nombre_o_telefono_no_suma` |
| 3 | Máximo 7 actividades diarias | Se cuentan todas las del funcionario en la **fecha de la actividad**, incluidas las coordinaciones; la octava se rechaza | `test_maximo_siete_por_dia` |
| 4 | La semana (lunes a viernes) se cierra el lunes siguiente | Solo fechas de lunes a viernes y no futuras; desde el martes se rechazan fechas de la semana anterior; sin desbloqueos. También impide eliminar actividades de semanas cerradas | `test_fechas_no_validas`, `test_semana_cierra_el_lunes_siguiente`, `test_eliminar_actividad_de_semana_cerrada` |
| 5 | Las coordinaciones previas (correos, llamadas, invitaciones) no dan punto; solo la acción ejecutada | Tipo de registro «Coordinación previa» → 0 puntos | `test_coordinacion_previa_no_suma` |
| 7 | Tope de 120 % por ítem | Cumplimiento = mín(puntos ÷ meta ajustada, 1,2); el excedente se informa como «sobre el tope» | `test_cumplimiento_y_colores` |
| 8 | Las felicitaciones las informa el delegado, con respaldo formal | Ítem marcado «de felicitaciones»: solo roles con `actividades.aprobar`, con respaldo (PDF o imagen) obligatorio y el funcionario felicitado; el ítem no aparece para el funcionario | `test_felicitacion_solo_delegado`, `test_delegado_valida_felicitacion_con_respaldo` |
| 9 | Días libres, vacaciones, administrativos y licencias los ingresa el delegado para ajustar las metas | Módulo **Ausencias** (solo delegado o superior). Meta ajustada = meta × (días hábiles − días de ausencia) ÷ días hábiles | `test_ausencias_ajustan_la_meta`, `test_reglas_de_ausencias` |
| 10 | Los puntajes se ven como equipo | El dashboard por delegación suma los puntos y las metas ajustadas de todo el equipo por ítem | `test_vision_de_equipo_por_delegacion` |

## Otras definiciones

- **Puntaje:** cada actividad válida suma **1 punto** en su ítem.
- **Ítems y metas:** los ítems se basan en el descriptor de funciones. Las metas se definen en cada trimestre por **ítem y cargo**, y cada funcionario hereda la meta de su cargo.
- **Trimestres:** solo uno puede estar abierto, y solo en él se registran actividades.
- **Semáforo:** verde ≥ 100 %, amarillo de 70 % a 99 % y rojo < 70 %, siempre con texto e ícono. El total es el promedio de los ítems con meta.
- **Códigos:** cada actividad recibe `GES-00000` o `SOC-00000` según el ámbito de su ítem. Los compromisos del tubo reciben `TUB-00000`.
- **Organizaciones:** catálogo de Juntas de Vecinos y organizaciones funcionales (adulto mayor, deportivas, centros de madres / culturales / juveniles y comités).
- **Datos de prueba:** son ficticios. La base «JJVV sin verificar.xlsx» que menciona el correo no se recibió, por lo que puede importarse cuando esté disponible.
