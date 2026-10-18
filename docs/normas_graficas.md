# Aplicación de las normas gráficas institucionales

Referencia oficial: <https://laserena.cl/conocenos/normas-graficas>

## Elementos aplicados

| Elemento | Aplicación en el SGR |
|---|---|
| **Color corporativo** | Rojo Heráldico: HEX `#C41230` · RGB 196, 18, 48 · CMYK 0, 100, 63, 12 · Pantone 200 C. Se usa en la cabecera, el panel de acceso, los botones principales, los enlaces, el foco de teclado, los encabezados del Excel y SweetAlert2 (`static/css/sgr.css`, variable `--rojo`). |
| **Colores de apoyo** | Solo neutros: blanco, grises y negro. No se agregan colores ajenos a la marca: ni verdes ni azules para estados. El *hover* usa el mismo rojo oscurecido (`--rojo-oscuro`) y los fondos suaves usan el mismo rojo con transparencia. |
| **Logotipo** | Versión en blanco (escudo + «La Serena · Ilustre Municipalidad») sobre fondo Rojo Heráldico, en la cabecera y en las pantallas de acceso (`static/img/logo-la-serena-blanco.png`). Se conservan sus proporciones, sin deformarlo, recolorearlo ni ponerlo sobre fondos claros. |
| **Tipografía** | Títulos en **Montserrat** (500/600/700) y textos en **Open Sans** (400/600/700), ambas sans serif de licencia libre (OFL) incluidas en `static/vendor/fonts/`. |
| **SweetAlert2** | Botón de confirmación rojo, cancelar en gris, tipografías institucionales e iconos de éxito, error y advertencia en Rojo Heráldico. El tipo de mensaje se distingue por la forma del icono y el título, no solo por el color. |
| **Estados** | Texto con icono: «Activo» con check sobre fondo gris e «Inactivo» con pausa y borde rojo discontinuo. El color nunca es el único indicador. |
| **Distintivo de delegación** | Píldora blanca con icono de ubicación, código en rojo y nombre en negro, más el texto «Delegación activa» y un candado con la palabra «Fija» si el contexto es único. |

## Supuestos a confirmar por el equipo

Durante el desarrollo no fue posible descargar el manual desde laserena.cl, porque el entorno no tenía acceso a ese sitio. Por eso:

1. **Tipografía:** se eligieron Montserrat y Open Sans como sans serif institucionales de uso libre. Si el manual define otra familia, basta con reemplazar los archivos de `static/vendor/fonts/` y las variables `--fuente-titulo` y `--fuente-texto` de `static/css/sgr.css`.
2. **Logotipo:** se usó el archivo entregado por el equipo (versión en blanco). Si el manual exige un área de resguardo o un tamaño mínimo distinto, ajuste `.cabecera__marca img` (40 px de alto) y `.acceso__marca img`.
3. Las capturas de los diseños del anexo C son referenciales; la identidad final es la de este documento.
