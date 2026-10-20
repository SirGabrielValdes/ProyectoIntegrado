"""
Genera el Informe Etapa 2 (Word) sobre la plantilla INACAP entregada.

    python docs/informe_etapa2/generar_informe.py

Requiere: python-docx, LibreOffice (para calcular el índice) y las imágenes de
docs/informe_etapa2/imagenes (generadas con PlantUML desde diagramas/*.puml).
"""
import copy
import re
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Inches, Pt, RGBColor
from docx.enum.style import WD_STYLE_TYPE
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
import contenido as C  # noqa: E402

BASE = Path(__file__).resolve().parent
RAIZ = BASE.parents[1]
PLANTILLA = BASE / "plantilla_inacap.docx"
SALIDA = BASE / "Informe_Etapa2_SGR.docx"
IMG = BASE / "imagenes"
ROJO = "C41230"

figuras = [0]
tablas = [0]


# ----------------------------------------------------------------------------- utilidades
def estilos(doc):
    st = doc.styles
    # Título1 de la plantilla: agregar nivel de esquema para el índice.
    t1 = st["Título1"]
    ppr = t1.element.get_or_add_pPr()
    if ppr.find(qn("w:outlineLvl")) is None:
        o = OxmlElement("w:outlineLvl"); o.set(qn("w:val"), "0"); ppr.append(o)
    t1.font.name = "Calibri"; t1.font.size = Pt(14)

    def nuevo(nombre, tam, negrita, nivel=None, antes=6, despues=4, color=None):
        s = st.add_style(nombre, WD_STYLE_TYPE.PARAGRAPH)
        s.base_style = st["Normal"]
        s.font.name = "Calibri"; s.font.size = Pt(tam); s.font.bold = negrita
        if color:
            s.font.color.rgb = RGBColor.from_string(color)
        pf = s.paragraph_format
        pf.space_before = Pt(antes); pf.space_after = Pt(despues); pf.line_spacing = 1.0
        pf.keep_with_next = nivel is not None
        if nivel is not None:
            o = OxmlElement("w:outlineLvl"); o.set(qn("w:val"), str(nivel))
            s.element.get_or_add_pPr().append(o)
        return s

    nuevo("SGR Subtítulo", 12, True, nivel=1, antes=12, despues=6)
    nuevo("SGR Subtítulo 3", 11, True, nivel=2, antes=8, despues=4, color="404040")
    t = nuevo("SGR Texto", 11, False, antes=0, despues=6)
    t.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    nuevo("SGR Tabla", 9, False, antes=0, despues=0)
    c = nuevo("SGR Leyenda", 9.5, False, antes=2, despues=10)
    c.font.italic = True; c.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = nuevo("SGR Referencia", 11, False, antes=0, despues=0)
    r.paragraph_format.line_spacing = 2.0
    r.paragraph_format.left_indent = Cm(1.27); r.paragraph_format.first_line_indent = Cm(-1.27)
    for nombre, nivel in (("toc 2", 2), ("toc 3", 3)):
        try:
            s = st[nombre]
        except KeyError:
            s = st.add_style(nombre, WD_STYLE_TYPE.PARAGRAPH); s.base_style = st["Normal"]
        s.paragraph_format.left_indent = Cm(0.5 * (nivel - 1)); s.paragraph_format.space_after = Pt(2)


def numeracion_vinetas(doc):
    """Crea una numeración de viñetas propia en numbering.xml y devuelve su numId."""
    numbering = doc.part.numbering_part.element
    ids = [int(a.get(qn("w:abstractNumId"))) for a in numbering.findall(qn("w:abstractNum"))]
    nums = [int(n.get(qn("w:numId"))) for n in numbering.findall(qn("w:num"))]
    aid, nid = max(ids) + 1, max(nums) + 1
    xml = f'''<w:abstractNum xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" w:abstractNumId="{aid}">
      <w:multiLevelType w:val="hybridMultilevel"/>
      <w:lvl w:ilvl="0"><w:start w:val="1"/><w:numFmt w:val="bullet"/><w:lvlText w:val="•"/><w:lvlJc w:val="left"/>
        <w:pPr><w:ind w:left="567" w:hanging="283"/></w:pPr><w:rPr><w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/><w:color w:val="{ROJO}"/></w:rPr></w:lvl>
      <w:lvl w:ilvl="1"><w:start w:val="1"/><w:numFmt w:val="bullet"/><w:lvlText w:val="–"/><w:lvlJc w:val="left"/>
        <w:pPr><w:ind w:left="1134" w:hanging="283"/></w:pPr></w:lvl></w:abstractNum>'''
    from lxml import etree
    abstract = etree.fromstring(xml)
    primer_num = numbering.find(qn("w:num"))
    primer_num.addprevious(abstract)
    num = OxmlElement("w:num"); num.set(qn("w:numId"), str(nid))
    a = OxmlElement("w:abstractNumId"); a.set(qn("w:val"), str(aid)); num.append(a)
    numbering.append(num)
    return nid


class Informe:
    def __init__(self, doc, vinetas, toc):
        self.doc = doc
        self.vinetas = vinetas
        self.toc = toc  # lista de (nivel, texto, página)
        self.encabezados = []

    def h1(self, texto):
        p = self.doc.add_paragraph(texto, style="Título1")
        p.paragraph_format.page_break_before = True
        self.encabezados.append((1, texto))
        return p

    def h2(self, texto):
        self.encabezados.append((2, texto))
        return self.doc.add_paragraph(texto, style="SGR Subtítulo")

    def h3(self, texto):
        self.encabezados.append((3, texto))
        return self.doc.add_paragraph(texto, style="SGR Subtítulo 3")

    def p(self, texto, negrita_inicial=None):
        par = self.doc.add_paragraph(style="SGR Texto")
        if negrita_inicial:
            par.add_run(negrita_inicial).bold = True
        par.add_run(texto)
        return par

    def lista(self, items, nivel=0):
        for it in items:
            par = self.doc.add_paragraph(style="SGR Texto")
            par.paragraph_format.space_after = Pt(2)
            numpr = par._p.get_or_add_pPr().get_or_add_numPr()
            numpr.get_or_add_ilvl().val = nivel
            numpr.get_or_add_numId().val = self.vinetas
            if isinstance(it, tuple):
                par.add_run(it[0]).bold = True
                par.add_run(it[1])
            else:
                par.add_run(it)

    def leyenda_tabla(self, texto):
        tablas[0] += 1
        par = self.doc.add_paragraph(style="SGR Leyenda")
        par.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
        par.paragraph_format.keep_with_next = True
        par.paragraph_format.space_before = Pt(8); par.paragraph_format.space_after = Pt(3)
        r = par.add_run(f"Tabla {tablas[0]}. "); r.bold = True; r.italic = False
        par.add_run(texto)

    def tabla(self, titulo, encabezado, filas, anchos, nota=None):
        self.leyenda_tabla(titulo)
        t = self.doc.add_table(rows=1, cols=len(encabezado))
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        t.autofit = False
        bordes(t)
        for i, txt in enumerate(encabezado):
            celda(t.rows[0].cells[i], txt, anchos[i], cabecera=True)
        marcar_cabecera(t.rows[0])
        for fila in filas:
            cells = t.add_row().cells
            for i, txt in enumerate(fila):
                celda(cells[i], txt, anchos[i])
        fijar_anchos(t, anchos)
        if nota:
            n = self.doc.add_paragraph(style="SGR Tabla")
            n.paragraph_format.space_after = Pt(8)
            r = n.add_run("Nota. "); r.italic = True
            n.add_run(nota)
        else:
            self.doc.add_paragraph(style="SGR Tabla").paragraph_format.space_after = Pt(6)
        return t

    def figura(self, archivo, texto, ancho_max=16.0, alto_max=20.5):
        ruta = IMG / archivo
        w, h = Image.open(ruta).size
        ancho = min(ancho_max, alto_max * w / h)
        par = self.doc.add_paragraph(style="SGR Texto")
        par.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
        par.paragraph_format.keep_with_next = True
        par.add_run().add_picture(str(ruta), width=Cm(ancho))
        figuras[0] += 1
        ley = self.doc.add_paragraph(style="SGR Leyenda")
        r = ley.add_run(f"Figura {figuras[0]}. "); r.bold = True; r.italic = False
        ley.add_run(texto)

    def salto(self):
        self.doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)


def fijar_anchos(tabla, anchos):
    """Anchos explícitos (tblW, tblLayout fijo y tblGrid) para Word y LibreOffice."""
    tbl = tabla._tbl
    tblPr = tbl.tblPr
    total = sum(int(Cm(a).twips) for a in anchos)
    w = tblPr.find(qn("w:tblW"))
    if w is None:
        w = OxmlElement("w:tblW"); tblPr.append(w)
    w.set(qn("w:w"), str(total)); w.set(qn("w:type"), "dxa")
    lay = OxmlElement("w:tblLayout"); lay.set(qn("w:type"), "fixed"); tblPr.append(lay)
    grid = tbl.tblGrid
    for i, gc in enumerate(grid.findall(qn("w:gridCol"))):
        gc.set(qn("w:w"), str(int(Cm(anchos[i]).twips)))
    for fila in tabla.rows:
        for i, c in enumerate(fila.cells):
            c.width = Cm(anchos[i])


def bordes(tabla):
    tblPr = tabla._tbl.tblPr
    b = OxmlElement("w:tblBorders")
    for lado in ("top", "left", "bottom", "right", "insideH", "insideV"):
        e = OxmlElement(f"w:{lado}")
        e.set(qn("w:val"), "single"); e.set(qn("w:sz"), "4"); e.set(qn("w:color"), "BFBFBF")
        b.append(e)
    tblPr.append(b)
    mar = OxmlElement("w:tblCellMar")
    for lado, v in (("left", 70), ("right", 70), ("top", 30), ("bottom", 30)):
        e = OxmlElement(f"w:{lado}"); e.set(qn("w:w"), str(v)); e.set(qn("w:type"), "dxa"); mar.append(e)
    tblPr.append(mar)


def marcar_cabecera(fila):
    trPr = fila._tr.get_or_add_trPr()
    e = OxmlElement("w:tblHeader"); e.set(qn("w:val"), "true"); trPr.append(e)


def celda(c, texto, ancho_cm, cabecera=False):
    c.width = Cm(ancho_cm)
    c.paragraphs[0].style = "SGR Tabla"
    lineas = str(texto).split("\n")
    for i, linea in enumerate(lineas):
        par = c.paragraphs[0] if i == 0 else c.add_paragraph(style="SGR Tabla")
        r = par.add_run(linea)
        if cabecera:
            r.bold = True; r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
    if cabecera:
        tcPr = c._tc.get_or_add_tcPr()
        sh = OxmlElement("w:shd"); sh.set(qn("w:val"), "clear"); sh.set(qn("w:color"), "auto"); sh.set(qn("w:fill"), ROJO)
        tcPr.append(sh)


def reemplazar_textos(elemento, mapa):
    for t in elemento.iter(qn("w:t")):
        if t.text in mapa:
            t.text = mapa[t.text]
            t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")


def insertar_indice(doc, ancla, toc):
    """Campo TOC de Word con su resultado precalculado (actualizable con F9)."""
    def run_fld(tipo):
        r = OxmlElement("w:r"); f = OxmlElement("w:fldChar"); f.set(qn("w:fldCharType"), tipo); r.append(f); return r

    def par_vacio():
        return copy.deepcopy(ancla._p)

    nuevos = []
    p0 = OxmlElement("w:p")
    p0.append(run_fld("begin"))
    r = OxmlElement("w:r"); it = OxmlElement("w:instrText"); it.set(qn("xml:space"), "preserve")
    it.text = ' TOC \\o "1-3" \\h \\z \\u '; r.append(it); p0.append(r)
    p0.append(run_fld("separate"))
    nuevos.append(p0)
    for nivel, texto, pagina in toc:
        par = doc.add_paragraph(style=f"toc {nivel}")
        pPr = par._p.get_or_add_pPr()
        tabs = OxmlElement("w:tabs"); tab = OxmlElement("w:tab")
        tab.set(qn("w:val"), "right"); tab.set(qn("w:leader"), "dot"); tab.set(qn("w:pos"), "9350"); tabs.append(tab)
        pPr.append(tabs)
        rr = par.add_run(texto)
        if nivel == 1:
            rr.bold = True
        par.add_run("\t" + str(pagina))
        par._p.getparent().remove(par._p)
        nuevos.append(par._p)
    pf = OxmlElement("w:p"); pf.append(run_fld("end")); nuevos.append(pf)
    actual = ancla._p
    for n in nuevos:
        actual.addnext(n); actual = n
    # Primer elemento del índice va dentro del párrafo de inicio de campo:
    return actual


# ----------------------------------------------------------------------------- contenido
def construir(toc):
    figuras[0] = 0; tablas[0] = 0
    doc = Document(str(PLANTILLA))
    estilos(doc)
    vin = numeracion_vinetas(doc)
    cuerpo = doc.element.body

    # Portada y pie de página.
    reemplazar_textos(cuerpo, {
        "Informe Nombre del trabajo": C.TITULO,
        "Nombre de la unidad de aprendizaje": "Etapa 2 · Sistema de Gestión de Requerimientos (SGR) – Municipalidad de La Serena",
        "Asignatura: ": "Asignatura: Ingeniería de Software (TI2043)",
        "Sección: ": "Sección: [Sección]",
        " Nombre y apellidos": " [Nombre y apellidos del docente]",
        "Nombre de los integrantes del grupo:": "Nombre de los integrantes del grupo: [Integrante 1 – representante], [Integrante 2], [Integrante 3]",
        "Fecha de entrega": "Fecha de entrega: octubre de 2026",
    })
    for sec in doc.sections:
        for parte in (sec.footer, sec.first_page_footer, sec.header, sec.first_page_header):
            reemplazar_textos(parte._element, {"Nombre del informe": C.PIE})

    # Quitar índice de ejemplo e instrucciones de la plantilla (desde el párrafo 7).
    pars = doc.paragraphs
    titulo_contenido = pars[6]
    titulo_contenido.runs[0].text = "Índice de contenidos"
    for par in pars[7:]:
        par._p.getparent().remove(par._p)
    fin_indice = insertar_indice(doc, titulo_contenido, toc)

    inf = Informe(doc, vin, toc)

    # ---------------------------------------------------------------- I. Introducción
    inf.h1("Introducción")
    inf.p("El presente informe corresponde a la Etapa 2 del proyecto de Ingeniería de Software y documenta la planificación y el diseño "
          "del Sistema de Gestión de Requerimientos (SGR) de la Ilustre Municipalidad de La Serena. El SGR es una aplicación web que "
          "permite a las delegaciones municipales registrar la atención ciudadana, administrar los catálogos que la clasifican y "
          "controlar el acceso de los funcionarios según su rol y su delegación.")
    inf.p("En primer lugar, se describen las técnicas aplicadas para la toma de requerimientos (análisis documental y prototipado con "
          "validación del cliente), junto con la tabulación y el análisis de los datos obtenidos. A partir de ellos se presentan los "
          "requerimientos funcionales y no funcionales, las épicas, las historias de usuario con sus tareas y esfuerzo estimado, y el "
          "diagrama de requerimientos que relaciona los artefactos.")
    inf.p("En segundo lugar, se analizan tres metodologías de desarrollo (Cascada, Incremental y Scrum) y se justifica la selección de "
          "Scrum, describiendo las tareas y actividades de cada sprint y los recursos de software, hardware y humanos requeridos para el "
          "desarrollo y la operación. Finalmente, se presenta la propuesta de diseño mediante diagramas UML de casos de uso, clases, "
          "componentes y despliegue, y los wireframes trazados desde cada requerimiento hasta la interfaz del prototipo.")

    # ---------------------------------------------------------------- II. Objetivos
    inf.h1("Objetivos")
    inf.h2("2.1 Objetivo general")
    inf.p("Planificar y diseñar el producto software SGR para la Municipalidad de La Serena, mediante la captura y el análisis de "
          "requerimientos, la selección justificada de una metodología de desarrollo y la elaboración de modelos UML y wireframes "
          "que guíen su construcción.")
    inf.h2("2.2 Objetivos específicos")
    inf.lista([
        "Levantar los requerimientos del proyecto aplicando técnicas de toma de necesidades y validarlos con el cliente.",
        "Especificar requerimientos funcionales y no funcionales, épicas e historias de usuario con su esfuerzo estimado.",
        "Analizar al menos dos metodologías de desarrollo y justificar la seleccionada con sus tareas, actividades y recursos.",
        "Elaborar los diagramas UML de casos de uso, clases, componentes, despliegue y requerimientos.",
        "Diseñar los wireframes del front-end trazados hasta el requerimiento funcional que satisfacen.",
    ])

    # ---------------------------------------------------------------- III. Desarrollo
    inf.h1("Desarrollo")
    inf.h2("3.1 Contexto del proyecto")
    inf.p("Las delegaciones municipales de La Serena atienden diariamente solicitudes de vecinos (ayudas sociales, luminarias, retiro "
          "de residuos, trámites, entre otras). El cliente requiere un sistema único, accesible desde la web y desplegado en AWS, que "
          "registre cada atención con su solicitante, su clasificación y la delegación y funcionario responsables, respetando las "
          "normas gráficas institucionales y los permisos de cada perfil (superadministrador, coordinador, delegado municipal y "
          "funcionario).")
    inf.p("El alcance de esta etapa considera el acceso con recuperación de contraseña, seis mantenedores (Delegaciones, Roles, "
          "Usuarios, Ítems y metas, Tipo de Atención y Sub Atención), el ingreso de atención ciudadana y las plantillas navegables "
          "de los módulos futuros (Vecinos, Tipo de Gestión, Seguimiento, Reportes y Auditoría).")

    # ===== Actividad 1
    inf.h2("3.2 Actividad 1: Técnicas para la toma de requerimientos")
    inf.h3("3.2.1 Técnicas aplicadas y justificación")
    inf.p("El equipo seleccionó técnicas acordes con la disponibilidad del cliente y con la existencia de documentación formal del "
          "proyecto. Según Sommerville (2011), el análisis de documentos existentes y el prototipado son técnicas complementarias: la "
          "primera identifica requerimientos explícitos y la segunda permite validar los implícitos con los usuarios.")
    inf.tabla("Técnicas de toma de requerimientos", ["Técnica", "Justificación", "Instrumento", "Estado"], [
        ("Análisis documental", "El cliente entregó requisitos formales, diseños de referencia y normas gráficas. Permite extraer requerimientos explícitos y trazables a su fuente.",
         "Ficha de análisis documental (Tabla 2) y tabulación (Tablas 3 a 6)", "Aplicada"),
        ("Prototipado evolutivo", "Hace visibles los requerimientos para el cliente y reduce ambigüedades de interfaz y flujo antes de cerrar el diseño (Pressman, 2010).",
         "Prototipo funcional del SGR y protocolo de pruebas de aceptación", "Aplicada"),
        ("Validación con el cliente", "Confirma que los requerimientos interpretados corresponden a lo solicitado (Wiegers y Beatty, 2013).",
         "Pruebas de aceptación ligadas a cada requisito y acta de validación (Anexo C)", "Aplicada (pruebas); acta por firmar"),
        ("Entrevista semiestructurada", "Profundiza en el proceso real de atención con funcionarios de delegación.",
         "Guía de entrevista (Anexo A)", "Diseñada, pendiente de aplicación"),
        ("Encuesta", "Cuantifica prioridades y necesidades de un grupo mayor de usuarios.",
         "Cuestionario Likert (Anexo B)", "Diseñada, pendiente de aplicación"),
    ], [3.0, 6.5, 4.3, 2.7], nota="Las técnicas pendientes no se consideran en la tabulación; sus resultados se incorporarán al aplicarse.")

    inf.h3("3.2.2 Instrumento aplicado: ficha de análisis documental")
    inf.tabla("Ficha de análisis documental: fuentes revisadas", ["ID", "Documento", "Emisor", "Contenido relevante"],
              [f for f in C.FUENTES], [1.0, 6.0, 3.6, 5.9])
    inf.p("Para cada fuente se registró cada enunciado que expresara una capacidad del sistema (requerimiento funcional), una "
          "restricción de calidad (requerimiento no funcional) o una regla de negocio, junto con su ubicación en el documento. Los "
          "enunciados duplicados entre fuentes se consolidaron en un único requerimiento con fuente múltiple (por ejemplo, F1/F2).")

    inf.h3("3.2.3 Tabulación y análisis de los datos")
    # Tabulación automática a partir de los requerimientos especificados.
    por_epica = Counter(r[3] for r in C.RF)
    por_prioridad = Counter(r[5] for r in C.RF)
    por_fuente_rf = Counter(r[4] for r in C.RF)
    por_fuente_rnf = Counter(r[3] for r in C.RNF)
    sp_epica = Counter()
    for h in C.HU:
        sp_epica[h[1]] += h[5]
    inf.tabla("Requerimientos identificados por fuente", ["Fuente", "RF", "RNF", "Total"],
              [(f, por_fuente_rf.get(f, 0), por_fuente_rnf.get(f, 0), por_fuente_rf.get(f, 0) + por_fuente_rnf.get(f, 0))
               for f in sorted(set(por_fuente_rf) | set(por_fuente_rnf))]
              + [("Total", len(C.RF), len(C.RNF), len(C.RF) + len(C.RNF))], [4.0, 3.0, 3.0, 3.0])
    total_sp = sum(h[5] for h in C.HU)
    inf.tabla("Distribución por épica: requerimientos, historias y esfuerzo", ["Épica", "RF", "HU", "Puntos de historia", "% del esfuerzo"],
              [(f"{e[0]} {e[1]}", por_epica.get(e[0], 0), sum(1 for h in C.HU if h[1] == e[0]), sp_epica[e[0]],
                f"{100 * sp_epica[e[0]] / total_sp:.0f} %") for e in C.EPICAS]
              + [("Total", len(C.RF), len(C.HU), total_sp, "100 %")], [6.0, 1.6, 1.6, 3.0, 2.5])
    inf.tabla("Priorización MoSCoW de los requerimientos funcionales", ["Prioridad", "Cantidad", "%", "Requerimientos"],
              [(p, por_prioridad.get(p, 0), f"{100 * por_prioridad.get(p, 0) / len(C.RF):.0f} %",
                ", ".join(r[0] for r in C.RF if r[5] == p)) for p in ("Must", "Should", "Could")],
              [2.2, 2.0, 1.6, 10.7])
    con_f2 = sum(1 for r in C.RF if "F2" in r[4])
    must = 100 * por_prioridad.get("Must", 0) / len(C.RF)
    inf.p("Del análisis se desprende que el documento de requisitos del cliente (F1) es la fuente principal: está presente en todos los "
          f"requerimientos, y los diseños de referencia (F2) complementan {con_f2} de los {len(C.RF)} requerimientos funcionales con el detalle de la "
          f"interfaz. El {must:.0f} % de los requerimientos funcionales es de prioridad Must, lo que confirma que el núcleo de la entrega "
          "(acceso, mantenedores, atención y permisos) no admite postergación. Las épicas EP02 (estructura municipal y permisos) "
          "y EP01 (acceso y seguridad) concentran el mayor esfuerzo estimado, por lo que se planifican en los primeros sprints.",
          negrita_inicial="Análisis. ")
    inf.tabla("Ambigüedades detectadas y decisiones tomadas", ["Tema", "Hallazgo", "Decisión del equipo"],
              C.AMBIGUEDADES, [4.0, 5.0, 7.5])

    inf.h3("3.2.4 Requerimientos funcionales")
    inf.tabla("Requerimientos funcionales", ["ID", "Nombre", "Descripción", "Épica", "Fuente", "Prioridad"],
              [(r[0], r[1], r[2], r[3], r[4], r[5]) for r in C.RF], [1.3, 2.9, 7.8, 1.3, 1.4, 1.8])
    inf.h3("3.2.5 Requerimientos no funcionales")
    inf.tabla("Requerimientos no funcionales", ["ID", "Categoría", "Descripción", "Fuente"],
              C.RNF, [1.5, 2.6, 10.8, 1.6])

    inf.h3("3.2.6 Épicas, historias de usuario, tareas y esfuerzo")
    inf.p("El esfuerzo se estimó en puntos de historia (escala de Fibonacci: 1, 2, 3, 5, 8, 13) mediante Planning Poker, "
          "considerando complejidad, incertidumbre y volumen de trabajo (Cohn, 2004). Cada tarea se estimó además en horas para "
          "verificar la capacidad de cada sprint.")
    inf.tabla("Épicas del proyecto", ["ID", "Épica", "Descripción", "Requerimientos"],
              C.EPICAS, [1.3, 4.0, 7.0, 4.2])
    filas_hu = []
    for h in C.HU:
        tareas = "\n".join(f"• {t} ({hrs} h)" for t, hrs in h[6])
        filas_hu.append((h[0], h[1], f"Como {h[2]}, quiero {h[3]}, para {h[4]}.", tareas, h[5], sum(x[1] for x in h[6])))
    inf.tabla("Historias de usuario con sus tareas y esfuerzo", ["HU", "Épica", "Historia de usuario", "Tareas (horas)", "SP", "Horas"],
              filas_hu, [1.2, 1.3, 5.0, 6.6, 1.0, 1.4],
              nota=f"Total: {len(C.HU)} historias, {total_sp} puntos de historia y "
                   f"{sum(sum(x[1] for x in h[6]) for h in C.HU)} horas estimadas.")
    inf.tabla("Criterios de aceptación por historia de usuario", ["HU", "Criterios de aceptación"],
              [(h[0], h[7]) for h in C.HU], [1.5, 15.0])

    inf.h3("3.2.7 Diagrama de requerimientos")
    inf.p("La relación entre los artefactos (necesidad del cliente, requerimiento, épica, historia, caso de uso, wireframe, "
          "componente y prueba) se presenta en la sección 3.4.6, con el diagrama de requerimientos que asegura la trazabilidad "
          "de extremo a extremo.")

    inf.h3("3.2.8 Validación de los requerimientos con el cliente")
    inf.p("Los requerimientos se validaron contrastando el prototipo con los criterios del cliente: cada requisito del documento F1 "
          "se transformó en una o más pruebas de aceptación automatizadas, ejecutadas sobre el prototipo y registradas en una matriz "
          "con requisito, módulo, precondiciones, pasos, resultado esperado y obtenido.")
    matriz = (RAIZ / "docs" / "pruebas" / "matriz_pruebas_funcionales.md").read_text(encoding="utf-8")
    modulos = Counter()
    for linea in matriz.splitlines():
        if linea.startswith("| PF-"):
            col = [c.strip() for c in linea.strip("|").split("|")]
            modulos[(col[2], col[6])] += 1
    agrupado = Counter()
    for (mod, estado), n in modulos.items():
        agrupado[mod] += n
    aprobadas = sum(n for (m, e), n in modulos.items() if e == "Aprobada")
    inf.tabla("Resultados de la validación con pruebas de aceptación por módulo", ["Módulo", "Casos", "Aprobados"],
              sorted([(m, n, sum(v for (mm, e), v in modulos.items() if mm == m and e == "Aprobada"))
                      for m, n in agrupado.items()], key=lambda x: -x[1])
              + [("Total", sum(agrupado.values()), aprobadas)], [8.0, 3.0, 3.0],
              nota="Además se ejecutaron 12 pruebas de interfaz en navegador (Playwright), todas aprobadas. Fuente: matriz de pruebas del repositorio.")
    inf.p(f"El {100 * aprobadas / max(1, sum(agrupado.values())):.0f} % de los casos de aceptación resultó aprobado, lo que indica que la "
          "interpretación de los requerimientos es consistente con lo solicitado. Las decisiones de la Tabla 6 se presentarán al "
          "cliente en la sesión de validación formal (acta del Anexo C) para su aprobación.", negrita_inicial="Resultado. ")

    # ===== Actividad 2
    inf.h2("3.3 Actividad 2: Selección y justificación de la metodología")
    inf.h3("3.3.1 Metodologías analizadas")
    inf.p("Modelo secuencial en el que cada fase (requerimientos, diseño, implementación, pruebas, despliegue) comienza cuando termina "
          "la anterior. Ofrece control documental y es adecuado cuando los requisitos son estables; sin embargo, los errores de "
          "interpretación se detectan tarde y el cliente ve el producto solo al final (Pressman, 2010).",
          negrita_inicial="Cascada (estructurada). ")
    inf.p("Divide el sistema en incrementos planificados; cada incremento recorre las fases de cascada y entrega funcionalidad "
          "utilizable. Reduce el riesgo respecto de cascada y permite entregas parciales, aunque requiere definir la arquitectura y "
          "los incrementos al inicio, con menor flexibilidad ante cambios dentro de un incremento (Sommerville, 2011).",
          negrita_inicial="Incremental (estructurada). ")
    inf.p("Marco ágil iterativo e incremental que organiza el trabajo en sprints de duración fija con roles (Product Owner, Scrum "
          "Master, Developers), eventos (planificación, daily, revisión, retrospectiva) y artefactos (Product Backlog, Sprint Backlog, "
          "Incremento). Prioriza la entrega frecuente de valor y la adaptación a los cambios mediante inspección continua "
          "(Schwaber y Sutherland, 2020).", negrita_inicial="Scrum (ágil). ")
    inf.h3("3.3.2 Análisis comparativo")
    tot = [0, 0, 0]
    filas = []
    for crit, peso, a, b, c in C.COMPARACION:
        filas.append((crit, f"{peso} %", a, b, c))
        tot[0] += peso * a; tot[1] += peso * b; tot[2] += peso * c
    filas.append(("Puntaje ponderado (máx. 5,0)", "100 %", f"{tot[0] / 100:.2f}", f"{tot[1] / 100:.2f}", f"{tot[2] / 100:.2f}"))
    inf.tabla("Matriz de evaluación de metodologías (escala 1 a 5)", ["Criterio", "Peso", "Cascada", "Incremental", "Scrum"],
              filas, [7.0, 1.8, 2.4, 2.6, 2.4])
    inf.p(f"Scrum obtiene el mayor puntaje ({tot[2] / 100:.2f}), seguido de Incremental ({tot[1] / 100:.2f}) y Cascada "
          f"({tot[0] / 100:.2f}).", negrita_inicial="Resultado. ")

    inf.h3("3.3.3 Justificación de la metodología seleccionada: Scrum")
    inf.lista([
        ("Requisitos con decisiones abiertas: ", "el análisis documental detectó seis ambigüedades (Tabla 6) que se resuelven mejor validando incrementos con el cliente en cada revisión de sprint."),
        ("Evaluaciones periódicas: ", "el calendario académico exige entregas parciales verificables, que coinciden con el incremento de cada sprint."),
        ("Equipo pequeño y multifuncional: ", "tres integrantes pueden cubrir los roles de Scrum con comunicación directa y bajo costo de coordinación."),
        ("Backlog basado en historias de usuario: ", "las épicas e historias definidas en la Actividad 1 constituyen directamente el Product Backlog priorizado."),
        ("Calidad continua: ", "la Definición de Terminado incluye pruebas automatizadas, lo que permite detectar defectos en el mismo sprint."),
    ])
    inf.p("El modelo Incremental sería una alternativa válida, pero exige fijar los incrementos al inicio; Scrum mantiene la entrega "
          "incremental y agrega mecanismos de adaptación (revisión y retrospectiva) que este proyecto necesita.")

    inf.h3("3.3.4 Aplicación de Scrum en el proyecto")
    inf.tabla("Roles, eventos y artefactos de Scrum en el SGR", ["Elemento", "Aplicación en el proyecto"], [
        ("Product Owner", "Docente en representación de la Municipalidad: prioriza el backlog y acepta los incrementos."),
        ("Scrum Master", "Integrante representante del grupo: facilita los eventos, elimina impedimentos y es interlocutor con el docente."),
        ("Developers", "Los tres integrantes: análisis, desarrollo, pruebas, despliegue y documentación."),
        ("Sprint", "Dos semanas (el Sprint 2 dura tres semanas por las Fiestas Patrias)."),
        ("Sprint Planning", "Al inicio de cada sprint (2 h): selección de historias según la velocidad estimada (≈ 20 SP)."),
        ("Daily Scrum", "15 minutos, tres veces por semana, presencial o por chat del equipo."),
        ("Sprint Review", "Demostración del incremento al Product Owner y registro de observaciones."),
        ("Retrospectiva", "45 minutos al cierre del sprint: qué mantener, qué mejorar y acciones."),
        ("Product Backlog", "Épicas e historias priorizadas (Tablas 9 y 10) en un tablero GitHub Projects."),
        ("Sprint Backlog", "Historias del sprint descompuestas en tareas con horas (columnas: Por hacer, En curso, En revisión, Terminado)."),
        ("Incremento", "Versión desplegada y etiquetada en Git (por ejemplo, entrega-2)."),
        ("Definición de Terminado", "Código en la rama principal revisado por otro integrante, pruebas automatizadas aprobadas, mensajes SweetAlert2, template institucional aplicado y documentación actualizada."),
    ], [3.6, 12.9])

    inf.h3("3.3.5 Métodos y técnicas complementarias")
    inf.lista([
        ("Historias de usuario e INVEST: ", "redacción y refinamiento de requerimientos (Cohn, 2004)."),
        ("Planning Poker: ", "estimación colaborativa en puntos de historia."),
        ("Tablero Kanban: ", "visualización del flujo de tareas del sprint en GitHub Projects."),
        ("Control de versiones con Git: ", "ramas por funcionalidad, revisión mediante pull requests y etiquetas por entrega."),
        ("Pruebas automatizadas: ", "pruebas funcionales (Django TestCase), de interfaz (Playwright) y de estrés (Locust)."),
        ("Modelado UML: ", "casos de uso, clases, componentes y despliegue con PlantUML versionado en el repositorio."),
    ])

    inf.h3("3.3.6 Tareas y actividades: planificación de sprints")
    inf.tabla("Planificación de sprints (Primavera 2026)", ["Sprint", "Objetivo", "Fechas", "Historias / actividades", "SP"],
              C.SPRINTS, [1.8, 3.2, 2.6, 7.4, 1.5],
              nota=f"Velocidad promedio planificada: {total_sp / 5:.1f} SP por sprint de desarrollo. La segunda evaluación coincide con el cierre del Sprint 4.")
    inf.tabla("Actividades transversales por sprint", ["Actividad", "Responsable", "Frecuencia / momento"], [
        ("Refinamiento del backlog", "Product Owner y equipo", "Mitad de cada sprint (1 h)"),
        ("Diseño UML y wireframes de las historias", "Integrante 2", "Antes de iniciar cada historia"),
        ("Desarrollo y revisión de código", "Developers", "Continuo"),
        ("Pruebas funcionales y de interfaz", "Integrante 3", "Por cada historia terminada"),
        ("Despliegue en AWS", "Integrante 3", "Cierre de cada sprint"),
        ("Revisión con el cliente y actualización del informe", "Integrante 1", "Cierre de cada sprint"),
    ], [7.0, 4.5, 5.0])

    inf.h3("3.3.7 Recursos de software y hardware")
    inf.tabla("Recursos de software y hardware: mínimos y óptimos", ["Ámbito", "Recurso", "Mínimo", "Óptimo"],
              C.RECURSOS_SWHW, [2.3, 3.6, 5.2, 5.4])
    inf.h3("3.3.8 Recursos humanos")
    inf.tabla("Equipos de trabajo para desarrollo y operación", ["Ámbito", "Integrante / cargo", "Responsabilidades", "Dedicación"],
              C.RECURSOS_HUMANOS, [2.3, 4.2, 7.2, 2.8])

    # ===== Actividad 3
    inf.h2("3.4 Actividad 3: Propuesta de diseño en UML")
    inf.h3("3.4.1 Diagrama de casos de uso de alto nivel")
    inf.p("El diagrama general agrupa los casos de uso por épica. Los actores se organizan por herencia: cada rol hereda los casos "
          "del rol inferior, y el alcance efectivo de cada acción lo determina la matriz de permisos del rol.")
    inf.figura("cu_general.png", "Diagrama de casos de uso de alto nivel del SGR.", alto_max=19.5)
    inf.tabla("Descripción de los casos de uso de alto nivel", ["CU", "Nombre", "Actor principal", "Descripción", "RF"], [
        ("CU01", "Iniciar sesión", "Usuario municipal", "Ingreso con usuario o correo y contraseña.", "RF01, RF02"),
        ("CU02", "Recuperar contraseña", "Usuario municipal", "Restablece la clave mediante un código enviado al correo.", "RF04–RF06"),
        ("CU03", "Cerrar sesión", "Usuario municipal", "Finaliza la sesión y protege las rutas internas.", "RF03"),
        ("CU04", "Gestionar delegaciones", "Superadministrador", "CRUD de delegaciones municipales.", "RF07"),
        ("CU05", "Gestionar roles y permisos", "Superadministrador", "Define roles, permisos y alcance.", "RF08"),
        ("CU06", "Gestionar usuarios", "Coordinador", "CRUD de usuarios de sus delegaciones.", "RF09"),
        ("CU07", "Cambiar delegación activa", "Coordinador", "Selecciona el contexto entre sus delegaciones autorizadas.", "RF15, RF16"),
        ("CU08", "Gestionar ítems y metas", "Delegado municipal", "CRUD de ítems y metas.", "RF10"),
        ("CU09", "Gestionar tipos de atención", "Delegado municipal", "CRUD de tipos de atención.", "RF11"),
        ("CU10", "Gestionar sub atenciones", "Delegado municipal", "CRUD de sub atenciones asociadas a un tipo.", "RF12"),
        ("CU11", "Registrar atención", "Funcionario", "Registra la atención de un vecino.", "RF17, RF18"),
        ("CU12", "Consultar atenciones", "Funcionario", "Lista y consulta las atenciones de su delegación.", "RF19"),
        ("CU13", "Exportar listado a Excel", "Coordinador", "Exporta el filtro aplicado de un listado.", "RF13, RF14"),
    ], [1.3, 3.6, 3.2, 6.2, 2.2])

    inf.h3("3.4.2 Diagramas de casos de uso de detalle y especificación")
    inf.figura("cu_acceso.png", "Casos de uso de detalle de la épica EP01 Acceso y seguridad.", alto_max=12)
    ficha(inf, "CU01 Iniciar sesión", [
        ("Actor", "Usuario municipal (cualquier rol)"),
        ("Descripción", "El usuario ingresa al sistema con su usuario o correo y su contraseña."),
        ("Precondiciones", "La cuenta existe, está activa y tiene un rol activo y al menos una delegación autorizada."),
        ("Flujo normal", "1. El usuario abre la pantalla de inicio de sesión.\n2. Ingresa usuario o correo y contraseña.\n3. El sistema valida las credenciales y el estado de la cuenta.\n4. El sistema asigna la delegación activa y muestra el inicio con los menús de su rol."),
        ("Flujos alternativos", "3a. Credenciales incorrectas: mensaje genérico y se incrementa el contador de intentos.\n3b. Cuenta o rol inactivo: se informa y no se inicia sesión.\n3c. Se supera el máximo de intentos: bloqueo temporal (extend «Bloquear por intentos fallidos»)."),
        ("Postcondiciones", "Sesión iniciada con delegación activa validada en el servidor."),
        ("Requerimientos", "RF01, RF02, RF16, RNF01"),
    ])
    ficha(inf, "CU02 Recuperar contraseña", [
        ("Actores", "Usuario municipal; Servidor de correo (SMTP)"),
        ("Descripción", "El usuario restablece su contraseña mediante un código de 6 dígitos enviado a su correo."),
        ("Precondiciones", "El usuario no recuerda su contraseña y tiene acceso a su correo."),
        ("Flujo normal", "1. El usuario solicita el código ingresando su correo (CU02.1).\n2. El sistema responde con un mensaje genérico y envía el código si la cuenta está activa.\n3. El usuario ingresa el código (CU02.2); el sistema valida vigencia, intentos y uso único.\n4. El usuario crea una nueva contraseña que cumple la política (CU02.4).\n5. El sistema invalida el código y redirige al inicio de sesión."),
        ("Flujos alternativos", "3a. Código incorrecto: se informan los intentos restantes; al superar el máximo se bloquea la solicitud.\n3b. Código vencido: se ofrece reenviar (CU02.3), disponible tras la espera configurada.\n4a. Clave débil o confirmación distinta: se rechaza indicando el requisito incumplido."),
        ("Postcondiciones", "Contraseña actualizada; el código usado y la clave anterior dejan de ser válidos."),
        ("Requerimientos", "RF04, RF05, RF06, RNF03"),
    ])
    inf.figura("cu_mantenedor.png", "Casos de uso de detalle de CU06 Gestionar usuarios (patrón común de los seis mantenedores).", alto_max=14)
    ficha(inf, "CU06 Gestionar usuarios", [
        ("Actores", "Coordinador (alcance: sus delegaciones); Superadministrador (alcance global)"),
        ("Descripción", "El actor lista, crea, consulta, edita y elimina o desactiva usuarios."),
        ("Precondiciones", "Sesión iniciada con permisos usuarios.ver y la acción correspondiente."),
        ("Flujo normal", "1. El actor abre Usuarios; el sistema lista los usuarios de la delegación activa con búsqueda, filtros y paginador.\n2. El actor selecciona «Nuevo usuario» y completa nombre, usuario, correo, rol, delegaciones y contraseña.\n3. El sistema valida campos requeridos, formato, duplicados, alcance del rol y política de clave.\n4. El sistema guarda y confirma con SweetAlert2."),
        ("Flujos alternativos", "3a. Datos inválidos: se marcan los campos con su error y no se guarda.\n4a. Eliminar un usuario con atenciones: se rechaza y se ofrece desactivar.\n1a. Exportar a Excel (CU13) el filtro aplicado."),
        ("Postcondiciones", "Usuario registrado o actualizado dentro del alcance autorizado del actor."),
        ("Requerimientos", "RF09, RF13, RF14, RF16, RNF02"),
    ])
    inf.figura("cu_atencion.png", "Casos de uso de detalle de la épica EP04 Atención ciudadana.", alto_max=11)
    ficha(inf, "CU11 Registrar atención", [
        ("Actor", "Funcionario (y roles superiores con permiso atenciones.crear)"),
        ("Descripción", "El funcionario registra la atención de un vecino en su delegación activa."),
        ("Precondiciones", "Sesión iniciada; existen tipos y sub atenciones activos."),
        ("Flujo normal", "1. El funcionario abre «Ingresar atención».\n2. Busca al vecino por RUT o nombre y lo selecciona (CU11.1).\n3. Selecciona el Tipo de Atención; el sistema carga solo las sub atenciones activas de ese tipo (CU11.3).\n4. Selecciona la sub atención y describe la solicitud.\n5. El sistema asigna delegación, responsable y fecha desde la sesión, guarda y muestra el folio."),
        ("Flujos alternativos", "2a. El vecino no existe: se registra con RUT validado (CU11.2).\n3a. Cambia el tipo: se limpia la sub atención si deja de ser válida.\n5a. Doble envío: se informa el folio existente sin duplicar.\n1a. Cancelar: no se crea registro."),
        ("Postcondiciones", "Atención registrada con folio único y trazable a su delegación y responsable."),
        ("Requerimientos", "RF17, RF18, RNF02, RNF05"),
    ])

    inf.h3("3.4.3 Diagrama de clases")
    inf.p("El modelo de dominio representa las entidades persistentes del SGR. La clase abstracta Catalogo concentra los atributos "
          "comunes de los mantenedores; Usuario se relaciona con Rol (permisos y alcance) y con las delegaciones autorizadas; "
          "Atencion vincula al vecino, la clasificación, la delegación y el responsable.")
    inf.figura("clases.png", "Diagrama de clases del dominio del SGR.", alto_max=17)
    inf.h3("3.4.4 Diagrama de componentes")
    inf.p("La solución sigue una arquitectura web por capas: el navegador presenta el template institucional con SweetAlert2; nginx "
          "atiende los archivos estáticos y reenvía las solicitudes a gunicorn; la aplicación Django se divide en cuatro componentes "
          "(core, cuentas, catalogos, atenciones) que acceden a MySQL/MariaDB mediante el ORM.")
    inf.figura("componentes.png", "Diagrama de componentes del SGR.", alto_max=16)
    inf.h3("3.4.5 Diagrama de despliegue")
    inf.p("El sistema se despliega en una instancia Amazon EC2 con Ubuntu Server 24.04, protegida por un Security Group que solo "
          "permite HTTP (80) y SSH (22). En la misma instancia se ejecutan nginx, gunicorn (gestionado por systemd) y MariaDB; el "
          "correo de recuperación se envía por SMTP seguro (puerto 587).")
    inf.figura("despliegue.png", "Diagrama de despliegue del SGR en AWS.", alto_max=15)
    inf.h3("3.4.6 Diagrama de requerimientos")
    inf.p("El diagrama de requerimientos muestra cómo una necesidad del cliente deriva en requerimientos, que se trazan a épicas, "
          "historias de usuario, casos de uso y wireframes, y que son satisfechos por un componente y verificados por pruebas. Se "
          "ilustran las cadenas de la atención ciudadana (EP04) y del acceso seguro (EP01).")
    inf.figura("requerimientos.png", "Diagrama de requerimientos: trazabilidad entre artefactos.", alto_max=17)

    inf.h3("3.4.7 Wireframes y trazabilidad")
    inf.p("Cada wireframe se diseñó a partir de un requerimiento funcional y se trazó hasta su épica y sus casos de uso de alto "
          "nivel y específico. Luego se implementó en el prototipo front-end aplicando las normas gráficas institucionales.")
    inf.tabla("Trazabilidad del requerimiento funcional al wireframe", ["RF", "Épica", "CU alto nivel", "CU específico", "Wireframe", "Prototipo"], [
        ("RF01 Iniciar sesión", "EP01", "CU01 Iniciar sesión", "CU01 (flujo normal)", "WF01 Login", "Figura 10"),
        ("RF05 Validar código", "EP01", "CU02 Recuperar contraseña", "CU02.2 Validar código", "WF02 Validar código", "Figura 12"),
        ("RF09 / RF13 Gestionar usuarios y buscar", "EP02 / EP05", "CU06 Gestionar usuarios", "CU06.1 Listar y buscar", "WF03 Listado", "Figura 14"),
        ("RF17 Registrar atención", "EP04", "CU11 Registrar atención", "CU11.3 Tipo y sub atención", "WF04 Ingreso de atención", "Figura 16"),
    ], [3.6, 1.9, 3.1, 3.2, 2.7, 2.0])
    pares = [
        ("wf01_login.png", "Wireframe WF01 Iniciar sesión (RF01 · EP01 · CU01).", "prototipo/01_login.png", "Prototipo de WF01: pantalla de inicio de sesión."),
        ("wf02_codigo.png", "Wireframe WF02 Validar código (RF05 · EP01 · CU02.2).", "prototipo/06_validar_codigo.png", "Prototipo de WF02: validación del código de 6 dígitos."),
        ("wf03_listado.png", "Wireframe WF03 Listado de mantenedor (RF09/RF13 · EP02 · CU06.1).", "prototipo/09_items_filtro_pagina2.png", "Prototipo de WF03: listado con búsqueda, filtros, exportación y paginador."),
        ("wf04_atencion.png", "Wireframe WF04 Ingreso de atención (RF17 · EP04 · CU11.3).", "prototipo/17_ingreso_atencion.png", "Prototipo de WF04: ingreso de atención con tipo y sub atención dependiente."),
    ]
    for wf, t1, proto, t2 in pares:
        inf.figura(wf, t1, ancho_max=16 if "listado" in wf else 13.5, alto_max=10)
        inf.figura(proto, t2, ancho_max=15.5, alto_max=11)

    # ---------------------------------------------------------------- IV. Conclusiones
    inf.h1("Conclusiones")
    inf.p("El trabajo permitió transformar la documentación entregada por el cliente en un conjunto trazable de 20 requerimientos "
          "funcionales y 12 no funcionales, organizados en 6 épicas y 18 historias de usuario estimadas en "
          f"{total_sp} puntos de historia. El análisis documental resultó adecuado por la existencia de requisitos formales, y el "
          "prototipado con pruebas de aceptación permitió validar la interpretación del equipo con evidencia objetiva.")
    inf.p("El análisis comparativo justificó la elección de Scrum frente a Cascada e Incremental, principalmente por la necesidad de "
          "validar con el cliente las decisiones abiertas y de entregar incrementos alineados con las evaluaciones. La planificación "
          "en cinco sprints de desarrollo, con su capacidad y recursos definidos, otorga un marco realista para el equipo de tres "
          "integrantes.")
    inf.p("Los diagramas UML de casos de uso, clases, componentes, despliegue y requerimientos, junto con los wireframes trazados hasta "
          "el prototipo, conforman una propuesta de diseño coherente con la implementación. Como trabajo futuro se propone aplicar la "
          "entrevista y la encuesta diseñadas para incorporar la visión directa de los funcionarios, formalizar la validación con el "
          "acta del Anexo C y completar los módulos que hoy se presentan como plantillas (Vecinos, Seguimiento, Reportes y Auditoría).")

    # ---------------------------------------------------------------- V. Glosario
    inf.h1("Glosario")
    inf.tabla("Glosario de términos", ["Término", "Definición"], C.GLOSARIO, [3.8, 12.7])

    # ---------------------------------------------------------------- VI. Referencias
    inf.h1("Referencias bibliográficas")
    for autor, titulo, resto in C.REFERENCIAS:
        par = doc.add_paragraph(style="SGR Referencia")
        par.add_run(autor); par.add_run(titulo).italic = True; par.add_run(resto)

    # ---------------------------------------------------------------- VII. Anexos
    inf.h1("Anexos")
    inf.h2("Anexo A. Guía de entrevista semiestructurada (diseñada, pendiente de aplicación)")
    inf.p("Dirigida a funcionarios y delegados municipales. Duración estimada: 30 minutos. Registro: notas y grabación con consentimiento.")
    inf.lista([
        "¿Cómo registra hoy la atención de un vecino y qué datos solicita?",
        "¿Qué tipos de atención son los más frecuentes en su delegación?",
        "¿Cómo identifica al vecino (RUT, nombre, dirección) y qué problemas tiene al hacerlo?",
        "¿Quién revisa o hace seguimiento de las atenciones registradas?",
        "¿Trabaja para más de una delegación? ¿Cómo se organiza en ese caso?",
        "¿Qué información necesitaría exportar o reportar y con qué frecuencia?",
        "¿Desde qué dispositivos accedería al sistema (computador, tablet, móvil)?",
        "¿Qué dificultades ha tenido con contraseñas o accesos a otros sistemas municipales?",
        "¿Qué funcionalidad considera imprescindible para la primera versión?",
        "¿Qué otra observación desea agregar?",
    ])
    inf.h2("Anexo B. Encuesta a funcionarios (diseñada, pendiente de aplicación)")
    inf.p("Escala Likert de 1 (muy en desacuerdo / nada importante) a 5 (muy de acuerdo / muy importante). Tabulación prevista: "
          "frecuencia, promedio y desviación estándar por ítem.")
    inf.tabla("Ítems de la encuesta y plantilla de tabulación", ["N.º", "Ítem", "Promedio", "Desv. est."], [
        ("1", "Es importante registrar cada atención con el vecino identificado por RUT.", "—", "—"),
        ("2", "Es importante clasificar las atenciones por tipo y sub atención.", "—", "—"),
        ("3", "Es importante ver siempre en qué delegación estoy trabajando.", "—", "—"),
        ("4", "Es importante exportar los listados a Excel.", "—", "—"),
        ("5", "Es importante recuperar mi contraseña sin depender de soporte.", "—", "—"),
        ("6", "Usaría el sistema desde un teléfono móvil.", "—", "—"),
        ("7", "Los mensajes de confirmación y error me ayudan a no cometer errores.", "—", "—"),
        ("8", "Ordene por prioridad: seguimiento, reportes, auditoría, catálogo de vecinos.", "—", "—"),
    ], [1.2, 10.8, 2.2, 2.3], nota="Las columnas de resultados se completarán al aplicar el instrumento; no se informan datos no recolectados.")
    inf.h2("Anexo C. Acta de validación de requerimientos con el cliente")
    inf.tabla("Acta de validación", ["Campo", "Registro"], [
        ("Fecha y lugar", "[dd/mm/2026] – [lugar o videollamada]"),
        ("Participantes", "Docente / representante municipal: [nombre]. Equipo: [integrantes]"),
        ("Material revisado", "Requerimientos (Tablas 7 y 8), historias de usuario (Tabla 10), prototipo desplegado y decisiones de la Tabla 6"),
        ("Requerimientos aprobados", "[ ] Todos   [ ] Con observaciones (detallar)"),
        ("Observaciones y cambios solicitados", "[ ]"),
        ("Firma del cliente", "____________________"),
    ], [4.5, 12.0])
    return doc, inf.encabezados


def ficha(inf, titulo, filas):
    inf.tabla(f"Especificación del caso de uso {titulo}", ["Campo", "Descripción"], filas, [3.2, 13.3])


# ----------------------------------------------------------------------------- índice en dos pasadas
def paginas(docx):
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(["soffice", "--headless", "--convert-to", "pdf", "--outdir", tmp, str(docx)],
                       check=True, capture_output=True, timeout=300)
        pdf = Path(tmp) / (Path(docx).stem + ".pdf")
        texto = subprocess.run(["pdftotext", "-layout", str(pdf), "-"], capture_output=True, text=True).stdout
    return texto.split("\f")


def numerar(encabezados):
    romanos = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII"]
    res, i = [], 0
    for nivel, texto in encabezados:
        if nivel == 1:
            res.append((1, f"{romanos[i]}. {texto}", texto)); i += 1
        else:
            res.append((nivel, texto, texto))
    return res


def main():
    _, enc = construir([])
    entradas = numerar(enc)
    toc = [(n, t, 0) for n, t, _ in entradas]
    doc, _ = construir(toc)
    doc.save(SALIDA)
    pags = paginas(SALIDA)
    inicio = 0
    # Saltar portada e índice: buscar desde la primera página que contenga «Introducción» como título.
    for i, pg in enumerate(pags):
        if re.search(r"^\s*I\.\s+Introducción\s*$", pg, re.M):
            inicio = i
            break
    toc, desde = [], inicio
    for nivel, visible, buscar in entradas:
        patron = re.compile(r"^\s*(?:[IVX]+\.\s+)?" + re.escape(buscar[:60]), re.M)
        for i in range(desde, len(pags)):
            if patron.search(pags[i]):
                toc.append((nivel, visible, i + 1)); desde = i
                break
        else:
            toc.append((nivel, visible, "")); print("No se encontró:", buscar)
    doc, _ = construir(toc)
    doc.save(SALIDA)
    print(f"Informe generado: {SALIDA} ({len(pags)} páginas, {figuras[0]} figuras, {tablas[0]} tablas)")


if __name__ == "__main__":
    main()
