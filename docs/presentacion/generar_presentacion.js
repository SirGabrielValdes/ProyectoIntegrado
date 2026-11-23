// Presentación SGR · Tercera evaluación (máx. 10 minutos)
const pptxgen = require("pptxgenjs");
const React = require("react");
const RDS = require("react-dom/server");
const sharp = require("sharp");
const fa = require("react-icons/fa6");
const path = require("path");
const { applyTheme } = require(process.env.SKILL + "/scripts/apply_theme.js");

const REPO = "/home/user/ProyectoIntegrado";
const EVID = REPO + "/docs/evidencias/";
const SALIDA = process.argv[2];
const TABLERO = process.argv[3];

const HEX = { rojo: "C41230", rojoOsc: "8E0D23", tinta: "2B2B2B", gris: "6E6E6E", rosa: "F6E1E5", claro: "F4F2F2", blanco: "FFFFFF", borde: "D9D9D9" };
const THEME = {
  name: "SGR La Serena",
  headFontFace: "Calibri",
  bodyFontFace: "Calibri",
  colors: {
    dk1: HEX.tinta, lt1: HEX.blanco, dk2: HEX.rojoOsc, lt2: HEX.claro,
    accent1: HEX.rojo, accent2: HEX.gris, accent3: HEX.rosa, accent4: "3D3D3D", accent5: "BDBDBD", accent6: HEX.rojoOsc,
    hlink: HEX.rojo, folHlink: HEX.rojoOsc,
  },
};

async function icono(nombre, color, px = 256) {
  const svg = RDS.renderToStaticMarkup(React.createElement(fa[nombre], { color: "#" + color, size: px }));
  const buf = await sharp(Buffer.from(svg)).png().toBuffer();
  return "image/png;base64," + buf.toString("base64");
}
async function dims(f) { const m = await sharp(f).metadata(); return { w: m.width, h: m.height }; }
// Encaja una imagen en una caja manteniendo proporción (centrada).
async function encajar(f, x, y, w, h) {
  const d = await dims(f); const r = Math.min(w / d.w, h / d.h);
  const iw = d.w * r, ih = d.h * r;
  return { x: x + (w - iw) / 2, y: y + (h - ih) / 2, w: iw, h: ih };
}

(async () => {
  const pres = new pptxgen();
  pres.layout = "LAYOUT_WIDE"; // 13.33 x 7.5
  pres.title = "Sistema de Gestión de Requerimientos (SGR)";
  pres.author = "Gabriel Valdes, Valentina Moreno";
  pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
  const C = pres.SchemeColor;
  const LOGO = REPO + "/static/img/logo-la-serena-blanco.png";
  const logoDim = await dims(LOGO);

  // ---------- Layouts ----------
  pres.defineSlideMaster({
    title: "PORTADA", background: { color: C.accent1 },
    objects: [
      { image: { path: LOGO, x: 0.7, y: 0.6, w: 2.6, h: 2.6 * logoDim.h / logoDim.w } },
      { placeholder: { options: { name: "title", type: "title", x: 0.7, y: 2.2, w: 11.5, h: 1.9, fontSize: 40, bold: true, color: C.background1, valign: "bottom", align: "left", margin: 0 }, text: "" } },
      { placeholder: { options: { name: "body", type: "body", x: 0.7, y: 4.25, w: 11.5, h: 0.6, fontSize: 20, color: C.background1, margin: 0 }, text: "" } },
    ],
  });
  pres.defineSlideMaster({
    title: "CONTENIDO", background: { color: C.background1 },
    margin: [0.5, 0.6, 0.6, 0.6],
    objects: [
      { placeholder: { options: { name: "title", type: "title", x: 0.6, y: 0.4, w: 12.1, h: 0.8, fontSize: 34, bold: true, color: C.text1, valign: "middle", align: "left", margin: 0 }, text: "" } },
      { text: { text: "SGR · Ilustre Municipalidad de La Serena · Ingeniería de Software TI3043", options: { x: 0.6, y: 7.0, w: 9, h: 0.3, fontSize: 10, color: C.accent2, margin: 0 } } },
    ],
    slideNumber: { x: 12.2, y: 7.0, w: 0.5, h: 0.3, fontSize: 10, color: C.accent2, align: "right" },
  });
  pres.defineSlideMaster({
    title: "CIERRE", background: { color: C.accent1 },
    objects: [
      { placeholder: { options: { name: "title", type: "title", x: 0.7, y: 0.5, w: 12, h: 0.9, fontSize: 36, bold: true, color: C.background1, align: "left", margin: 0 }, text: "" } },
      { image: { path: LOGO, x: 10.6, y: 6.35, w: 2.0, h: 2.0 * logoDim.h / logoDim.w } },
    ],
  });
  pres.defineSlideMaster({
    title: "REFERENCIAS", background: { color: C.background1 },
    objects: [
      { placeholder: { options: { name: "title", type: "title", x: 0.6, y: 0.4, w: 12.1, h: 0.8, fontSize: 30, bold: true, color: C.text1, align: "left", margin: 0 }, text: "" } },
      { placeholder: { options: { name: "body", type: "body", x: 0.6, y: 1.35, w: 12.1, h: 5.6, fontSize: 12, color: C.text1, valign: "top", margin: 0 }, text: "" } },
    ],
    slideNumber: { x: 12.2, y: 7.0, w: 0.5, h: 0.3, fontSize: 10, color: C.accent2, align: "right" },
  });

  // ---------- Componentes ----------
  const sombra = () => ({ type: "outer", color: "000000", blur: 6, offset: 2, angle: 90, opacity: 0.18 });
  async function circuloIcono(s, nombre, x, y, d = 0.62, fondo = C.accent1, color = HEX.blanco) {
    s.addShape(pres.shapes.OVAL, { x, y, w: d, h: d, fill: { color: fondo }, line: { color: fondo }, objectName: "Círculo " + nombre });
    const p = d * 0.26;
    s.addImage({ data: await icono(nombre, color), x: x + p, y: y + p, w: d - 2 * p, h: d - 2 * p, altText: "Ícono" });
  }
  async function captura(s, f, x, y, w, h, alt) {
    const b = await encajar(f, x, y, w, h);
    s.addShape(pres.shapes.RECTANGLE, { ...b, fill: { color: C.background1 }, line: { color: HEX.borde, width: 0.75 }, shadow: sombra(), objectName: "Marco " + alt });
    s.addImage({ path: f, ...b, altText: alt });
    return b;
  }
  function tarjeta(s, x, y, w, h, nombre, fondo = C.background2) {
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.12, fill: { color: fondo }, line: { color: fondo }, objectName: nombre });
  }
  const T = (s, text, o) => s.addText(text, { isTextBox: true, margin: 0, color: C.text1, fontSize: 15, valign: "top", ...o });

  // ===== 1. Portada =====
  pres.addSection({ title: "Inicio" });
  let s = pres.addSlide({ masterName: "PORTADA", sectionTitle: "Inicio" });
  s.addText("Sistema de Gestión de Requerimientos (SGR)", { placeholder: "title" });
  s.addText("Desarrollo de prototipo y wireframes · Municipalidad de La Serena · Tercera evaluación", { placeholder: "body" });
  T(s, [
    { text: "Gabriel Valdes · Valentina Moreno", options: { bold: true, breakLine: true } },
    { text: "Ingeniería de Software (Sección TI3043)", options: { breakLine: true } },
    { text: "Profesor: Francisco Gabriel Caiceo León", options: { breakLine: true } },
    { text: "16 de noviembre de 2026" },
  ], { x: 0.7, y: 5.3, w: 6.5, h: 1.5, fontSize: 15, color: C.background1, paraSpaceAfter: 3 });
  const pf = await encajar(EVID + "01_login.png", 8.3, 4.95, 4.5, 2.2);
  s.addShape(pres.shapes.RECTANGLE, { ...pf, fill: { color: C.background1 }, line: { color: C.background1, width: 2 }, shadow: sombra(), objectName: "Marco portada" });
  s.addImage({ path: EVID + "01_login.png", ...pf, altText: "Pantalla de inicio de sesión del SGR" });

  // ===== 2. Qué es el SGR =====
  pres.addSection({ title: "Contexto" });
  s = pres.addSlide({ masterName: "CONTENIDO", sectionTitle: "Contexto" });
  s.addText("Qué es el SGR", { placeholder: "title" });
  T(s, "Plataforma web para registrar y dar seguimiento a la atención ciudadana en las delegaciones municipales.", { x: 0.6, y: 1.45, w: 5.0, h: 1.0, fontSize: 18 });
  const puntos2 = [
    ["FaBuilding", "Continuación de la Etapa 2", "Allí planificamos y diseñamos; ahora mostramos cómo lo construimos."],
    ["FaListCheck", "Qué presentamos", "Requisitos cumplidos, Scrum, calidad y seguridad."],
    ["FaGlobe", "Uso por internet", "Cada funcionario entra con su usuario desde cualquier delegación."],
  ];
  for (let i = 0; i < puntos2.length; i++) {
    const y = 2.75 + i * 1.3;
    await circuloIcono(s, puntos2[i][0], 0.6, y);
    T(s, [{ text: puntos2[i][1], options: { bold: true, breakLine: true, fontSize: 16 } }, { text: puntos2[i][2], options: { color: C.accent2 } }], { x: 1.45, y: y - 0.02, w: 4.2, h: 1.1 });
  }
  await captura(s, EVID + "04_inicio_coordinador.png", 6.1, 1.45, 6.6, 5.2, "Pantalla de inicio del coordinador");

  // ===== 3. Decisiones de la Etapa 2 =====
  s = pres.addSlide({ masterName: "CONTENIDO", sectionTitle: "Contexto" });
  s.addText("Decisiones de la segunda evaluación", { placeholder: "title" });
  tarjeta(s, 0.6, 1.45, 6.0, 5.2, "Tarjeta gráfico");
  T(s, "Elegimos Scrum: mejor puntaje en nuestra tabla", { x: 0.9, y: 1.65, w: 5.4, h: 0.5, fontSize: 17, bold: true });
  s.addChart(pres.charts.BAR, [{ name: "Puntaje", labels: ["Scrum", "Incremental", "Cascada"], values: [4.5, 3.75, 2.0] }], {
    x: 0.8, y: 2.2, w: 5.6, h: 3.6, barDir: "col", chartColors: [HEX.rojo, "9A9A9A", "BDBDBD"], invertedColors: [HEX.rojo, "9A9A9A", "BDBDBD"],
    showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: "0.00", dataLabelFontSize: 14, dataLabelFontFace: "+mn-lt", dataLabelColor: HEX.tinta,
    catAxisLabelColor: HEX.tinta, catAxisLabelFontSize: 14, catAxisLabelFontFace: "+mn-lt", valAxisHidden: true, valAxisMaxVal: 5, valAxisMinVal: 0,
    valGridLine: { style: "none" }, catGridLine: { style: "none" }, showLegend: false, barGapWidthPct: 60,
  });
  T(s, "Dudas en algunos requisitos y equipo pequeño: entregas por sprint y corrección con el cliente.", { x: 0.9, y: 5.85, w: 5.4, h: 0.7, fontSize: 14, color: C.accent2 });
  const dec = [
    ["FaPenRuler", "UML y wireframes primero", "Para no malinterpretar lo que pedía el cliente."],
    ["FaDatabase", "Django + MariaDB", "Simple de manejar y con herramientas de seguridad incluidas."],
    ["FaCloud", "Servidor en AWS", "El cliente pedía usarlo por internet desde cualquier lugar."],
  ];
  for (let i = 0; i < dec.length; i++) {
    const y = 1.6 + i * 1.65;
    await circuloIcono(s, dec[i][0], 7.1, y, 0.7);
    T(s, [{ text: dec[i][1], options: { bold: true, breakLine: true, fontSize: 18 } }, { text: dec[i][2], options: { color: C.accent2, fontSize: 15 } }], { x: 8.05, y: y, w: 4.6, h: 1.3 });
  }

  // ===== 4. Tendencias tecnológicas =====
  pres.addSection({ title: "Fundamentos" });
  s = pres.addSlide({ masterName: "CONTENIDO", sectionTitle: "Fundamentos" });
  s.addText("Tendencias tecnológicas", { placeholder: "title" });
  const tend = [
    ["FaCloud", "Cloud computing", "Recursos de computación por internet, pagando solo lo que se usa.", "Crecer o achicar según la demanda y gastar menos en equipos."],
    ["FaGlobe", "SaaS", "Software desde el navegador, sin instalar nada (como Microsoft 365).", "Así usan el SGR los funcionarios desde cualquier delegación."],
    ["FaServer", "IaaS", "Arrendar infraestructura, por ejemplo un servidor virtual.", "El SGR corre en Amazon EC2; configuramos sistema, web y base de datos."],
  ];
  for (let i = 0; i < 3; i++) {
    const x = 0.6 + i * 4.1;
    tarjeta(s, x, 1.45, 3.8, 4.25, "Tarjeta " + tend[i][1]);
    await circuloIcono(s, tend[i][0], x + 0.35, 1.75, 0.8);
    T(s, tend[i][1], { x: x + 0.35, y: 2.75, w: 3.1, h: 0.5, fontSize: 22, bold: true, color: C.accent1 });
    T(s, tend[i][2], { x: x + 0.35, y: 3.3, w: 3.1, h: 1.1, fontSize: 15 });
    T(s, [{ text: "En el SGR: ", options: { bold: true } }, { text: tend[i][3] }], { x: x + 0.35, y: 4.45, w: 3.1, h: 1.1, fontSize: 14, color: C.accent2 });
  }
  await circuloIcono(s, "FaTriangleExclamation", 0.6, 6.0, 0.5, C.accent3, HEX.rojo);
  T(s, "Desventaja: dependemos del proveedor y la seguridad es compartida. AWS protege los equipos físicos; la configuración y los datos son nuestra responsabilidad.", { x: 1.25, y: 5.98, w: 11.4, h: 0.6, fontSize: 14, valign: "middle" });

  // ===== 5. Confiabilidad y ética =====
  s = pres.addSlide({ masterName: "CONTENIDO", sectionTitle: "Fundamentos" });
  s.addText("Confiabilidad y ética profesional", { placeholder: "title" });
  tarjeta(s, 0.6, 1.45, 4.6, 5.2, "Tarjeta confiabilidad", C.accent1);
  await circuloIcono(s, "FaShieldHalved", 0.95, 1.8, 0.8, C.background1, HEX.rojo);
  T(s, "¿Por qué un sistema confiable?", { x: 0.95, y: 2.85, w: 3.9, h: 0.9, fontSize: 21, bold: true, color: C.background1 });
  T(s, [
    { text: "Evita perder registros de atenciones", options: { bullet: true, breakLine: true } },
    { text: "Mantiene la confianza de los vecinos", options: { bullet: true, breakLine: true } },
    { text: "Ayuda a cumplir las leyes de datos personales", options: { bullet: true } },
  ], { x: 0.95, y: 3.85, w: 3.9, h: 2.5, fontSize: 16, color: C.background1, paraSpaceAfter: 8 });
  T(s, "Seguimos los códigos de ética de la ACM y del IEEE: no causar daño, respetar la privacidad y ser honestos.", { x: 5.7, y: 1.5, w: 7.0, h: 0.8, fontSize: 16 });
  const etica = [
    ["FaCircleCheck", "No mostramos «éxito» si algo falló"],
    ["FaUserShield", "Al recuperar la contraseña no se dice si el correo existe"],
    ["FaLock", "Solo pedimos y exportamos los datos necesarios"],
    ["FaEye", "Las pantallas que aún no funcionan lo dicen claramente"],
  ];
  for (let i = 0; i < 4; i++) {
    const x = 5.7 + (i % 2) * 3.55, y = 2.55 + Math.floor(i / 2) * 2.05;
    tarjeta(s, x, y, 3.35, 1.85, "Tarjeta ética " + (i + 1));
    await circuloIcono(s, etica[i][0], x + 0.25, y + 0.25, 0.55);
    T(s, etica[i][1], { x: x + 0.25, y: y + 0.95, w: 2.9, h: 0.8, fontSize: 15, bold: true });
  }

  // ===== 6. Leyes =====
  s = pres.addSlide({ masterName: "CONTENIDO", sectionTitle: "Fundamentos" });
  s.addText("Leyes que consideramos", { placeholder: "title" });
  const leyes = [
    ["Ley 21.459", "Delitos informáticos", "Sanciona el acceso ilícito, la interceptación y el daño a sistemas o datos.", "Login, permisos y validaciones. Pruebas de seguridad solo en nuestro sistema."],
    ["Ley 19.628", "Vida privada", "Ley vigente de protección de datos personales.", "Guardamos datos de vecinos: solo los necesarios y protegidos."],
    ["Ley 21.719", "Datos personales", "Reemplazará a la anterior: programada para el 1 de diciembre de 2026 (proyecto para postergarla a 2027).", "Diseñamos con sus principios: minimizar y proteger los datos."],
  ];
  for (let i = 0; i < 3; i++) {
    const x = 0.6 + i * 4.1;
    tarjeta(s, x, 1.45, 3.8, 4.4, "Tarjeta " + leyes[i][0]);
    await circuloIcono(s, "FaGavel", x + 0.35, 1.75, 0.7);
    T(s, leyes[i][0], { x: x + 1.2, y: 1.75, w: 2.4, h: 0.4, fontSize: 22, bold: true, color: C.accent1 });
    T(s, leyes[i][1], { x: x + 1.2, y: 2.15, w: 2.4, h: 0.35, fontSize: 14, color: C.accent2 });
    T(s, leyes[i][2], { x: x + 0.35, y: 2.75, w: 3.1, h: 1.5, fontSize: 15 });
    T(s, [{ text: "En el SGR: ", options: { bold: true } }, { text: leyes[i][3] }], { x: x + 0.35, y: 4.35, w: 3.1, h: 1.3, fontSize: 14, color: C.accent2 });
  }
  T(s, "No somos abogados: convertimos las leyes en requisitos técnicos del sistema.", { x: 0.6, y: 6.15, w: 12.1, h: 0.5, fontSize: 16, italic: true, color: C.accent1 });

  // ===== 7. Requisitos funcionales =====
  pres.addSection({ title: "Prototipo" });
  s = pres.addSlide({ masterName: "CONTENIDO", sectionTitle: "Prototipo" });
  s.addText("Requisitos funcionales implementados", { placeholder: "title" });
  T(s, "Prototipo hecho con Django 5.2 y MariaDB", { x: 0.6, y: 1.4, w: 7.5, h: 0.45, fontSize: 17, color: C.accent2 });
  const rf = [
    ["FaRightToBracket", "Inicio de sesión con bloqueo por intentos fallidos"],
    ["FaKey", "Recuperación de contraseña con código"],
    ["FaDatabase", "Mantenedores: delegaciones, roles, usuarios, ítems y metas, tipos y sub atenciones"],
    ["FaRotate", "Cambio de delegación activa"],
    ["FaUserShield", "Permisos según el rol"],
    ["FaFileExcel", "Registro y listado de atenciones, con exportación a Excel"],
  ];
  for (let i = 0; i < rf.length; i++) {
    const x = 0.6 + (i % 2) * 3.85, y = 2.05 + Math.floor(i / 2) * 1.55;
    await circuloIcono(s, rf[i][0], x, y, 0.6);
    T(s, rf[i][1], { x: x + 0.8, y: y - 0.02, w: 2.85, h: 1.3, fontSize: 15 });
  }
  tarjeta(s, 8.6, 1.45, 4.1, 5.2, "Tarjeta pruebas", C.accent3);
  T(s, "Cada requisito tiene pruebas", { x: 8.95, y: 1.7, w: 3.5, h: 0.5, fontSize: 17, bold: true });
  T(s, "71", { x: 8.95, y: 2.3, w: 3.5, h: 1.1, fontSize: 66, bold: true, color: C.accent1 });
  T(s, "pruebas de aceptación", { x: 8.95, y: 3.4, w: 3.5, h: 0.4, fontSize: 16 });
  T(s, "12", { x: 8.95, y: 4.15, w: 3.5, h: 1.1, fontSize: 66, bold: true, color: C.accent1 });
  T(s, "pruebas de interfaz", { x: 8.95, y: 5.25, w: 3.5, h: 0.4, fontSize: 16 });

  // ===== 8. Requisitos no funcionales =====
  s = pres.addSlide({ masterName: "CONTENIDO", sectionTitle: "Prototipo" });
  s.addText("Requisitos no funcionales", { placeholder: "title" });
  const rnf = [
    ["FaShieldHalved", "Seguridad", "Contraseñas cifradas y protección CSRF"],
    ["FaPalette", "Usabilidad", "Mensajes claros con SweetAlert2 y colores institucionales"],
    ["FaMobileScreen", "Adaptable", "Funciona en celular desde 390 px"],
    ["FaCodeBranch", "Mantenibilidad", "Código ordenado y con historial en Git"],
    ["FaGaugeHigh", "Rendimiento", "Prueba de estrés con 50 usuarios al mismo tiempo"],
  ];
  for (let i = 0; i < rnf.length; i++) {
    const y = 1.45 + i * 1.04;
    tarjeta(s, 0.6, y, 8.0, 0.88, "Tarjeta " + rnf[i][1]);
    await circuloIcono(s, rnf[i][0], 0.8, y + 0.14, 0.6);
    T(s, rnf[i][1], { x: 1.6, y: y, w: 2.2, h: 0.88, fontSize: 18, bold: true, valign: "middle" });
    T(s, rnf[i][2], { x: 3.8, y: y, w: 4.6, h: 0.88, fontSize: 15, valign: "middle" });
  }
  await captura(s, EVID + "22_movil_menu.png", 9.3, 1.45, 3.4, 5.15, "Vista del SGR en celular");

  // ===== 9. Del wireframe al prototipo =====
  s = pres.addSlide({ masterName: "CONTENIDO", sectionTitle: "Prototipo" });
  s.addText("Del wireframe al prototipo", { placeholder: "title" });
  T(s, "13 casos de uso, cada uno con su pantalla. Los mantenedores comparten el mismo diseño de listado (WF03).", { x: 0.6, y: 1.35, w: 12.1, h: 0.5, fontSize: 16, color: C.accent2 });
  await captura(s, REPO + "/docs/informe_etapa2/imagenes/wf04_atencion.png", 0.6, 2.05, 5.6, 4.3, "Wireframe WF04 ingreso de atención");
  await circuloIcono(s, "FaArrowRight", 6.35, 3.9, 0.6);
  await captura(s, EVID + "17_ingreso_atencion.png", 7.1, 2.05, 5.6, 4.3, "Pantalla de ingreso de atención");
  T(s, "WF04 · Ingreso de atención (CU11)", { x: 0.6, y: 6.45, w: 5.6, h: 0.35, fontSize: 13, color: C.accent2, align: "center" });
  T(s, "Prototipo funcionando", { x: 7.1, y: 6.45, w: 5.6, h: 0.35, fontSize: 13, color: C.accent2, align: "center" });

  // ===== 10. Pantallas del prototipo =====
  s = pres.addSlide({ masterName: "CONTENIDO", sectionTitle: "Prototipo" });
  s.addText("Pantallas del prototipo", { placeholder: "title" });
  const pant = [
    ["02_login_incorrecto_swal.png", "CU01 · Iniciar sesión"],
    ["07_nueva_clave.png", "CU02 · Recuperar contraseña"],
    ["11_confirmar_eliminar.png", "CU04–CU10 · Mantenedores"],
    ["15_advertencia_cambio_delegacion.png", "CU07 · Cambiar delegación activa"],
  ];
  for (let i = 0; i < 4; i++) {
    const x = 0.6 + (i % 2) * 6.2, y = 1.4 + Math.floor(i / 2) * 2.75;
    await captura(s, EVID + pant[i][0], x, y, 5.9, 2.2, pant[i][1]);
    T(s, pant[i][1], { x, y: y + 2.27, w: 5.9, h: 0.32, fontSize: 13, color: C.accent2, align: "center" });
  }

  // ===== 11. Scrum =====
  pres.addSection({ title: "Proceso y calidad" });
  s = pres.addSlide({ masterName: "CONTENIDO", sectionTitle: "Proceso y calidad" });
  s.addText("Cómo aplicamos Scrum", { placeholder: "title" });
  const scrum = [
    ["FaCalendarDays", "Sprints de dos semanas"],
    ["FaComments", "Revisión y retrospectiva al cerrar cada sprint"],
    ["FaClipboardCheck", "Terminado: código revisado por otro integrante y pruebas aprobadas"],
    ["FaPeopleGroup", "Product Owner: el docente · Scrum Master: representante del grupo"],
  ];
  for (let i = 0; i < scrum.length; i++) {
    const y = 1.5 + i * 1.25;
    await circuloIcono(s, scrum[i][0], 0.6, y, 0.65);
    T(s, scrum[i][1], { x: 1.45, y: y - 0.05, w: 4.1, h: 1.05, fontSize: 16, valign: "middle" });
  }
  if (TABLERO) {
    await captura(s, TABLERO, 5.9, 1.45, 6.8, 4.6, "Tablero del proyecto en GitHub Projects");
    T(s, "Tablero en GitHub Projects: 20 requisitos, 6 épicas y 18 historias de usuario", { x: 5.9, y: 6.2, w: 6.8, h: 0.45, fontSize: 13, color: C.accent2, align: "center" });
  }

  // ===== 12. Estándares de calidad =====
  s = pres.addSlide({ masterName: "CONTENIDO", sectionTitle: "Proceso y calidad" });
  s.addText("Estándares de calidad", { placeholder: "title" });
  const iso = [
    ["FaArrowsRotate" in fa ? "FaArrowsRotate" : "FaRotate", "ISO 12207", "Ciclo de vida: planificar, analizar, diseñar, construir, probar y desplegar"],
    ["FaListCheck", "ISO 25000", "Requisitos no funcionales agrupados por características de calidad"],
    ["FaCertificate", "ISO 9001", "Idea de mejora continua; no buscamos certificarnos"],
    ["FaVial", "Pruebas", "Funcionales, de interfaz y de estrés"],
    ["FaGitAlt", "Git", "Historial de cambios y revisiones de código"],
  ];
  const anchos = 12.1 / 5;
  for (let i = 0; i < iso.length; i++) {
    const x = 0.6 + i * anchos;
    tarjeta(s, x + 0.08, 1.6, anchos - 0.16, 4.6, "Tarjeta " + iso[i][1], i < 3 ? C.background2 : C.accent3);
    await circuloIcono(s, iso[i][0], x + 0.35, 1.95, 0.8);
    T(s, iso[i][1], { x: x + 0.35, y: 3.0, w: anchos - 0.6, h: 0.5, fontSize: 20, bold: true, color: C.accent1 });
    T(s, iso[i][2], { x: x + 0.35, y: 3.6, w: anchos - 0.6, h: 2.4, fontSize: 15 });
  }

  // ===== 13. Seguridad OWASP =====
  s = pres.addSlide({ masterName: "CONTENIDO", sectionTitle: "Proceso y calidad" });
  s.addText("Seguridad con OWASP Top 10", { placeholder: "title" });
  const ow = [
    ["Control de acceso", "Permisos revisados en el servidor; quien cambia la URL recibe error 403.", "Hecho"],
    ["Fallas de cifrado", "Contraseñas cifradas con PBKDF2. El servidor hoy usa HTTP.", "Falta HTTPS"],
    ["Inyección", "ORM de Django y validación de formularios.", "Hecho"],
    ["Autenticación", "Bloqueo por intentos fallidos y código de un solo uso de 10 minutos.", "Hecho"],
    ["Manejo de errores", "Mensajes que no muestran información interna.", "Hecho"],
    ["Registro de eventos", "Auditoría es solo una plantilla; falta definir qué se registra.", "Parcial"],
  ];
  const cab = { bold: true, color: HEX.blanco, fill: { color: HEX.rojo }, fontSize: 15, valign: "middle" };
  const filas = [[{ text: "Riesgo", options: cab }, { text: "Qué hicimos", options: cab }, { text: "Estado", options: { ...cab, align: "center" } }]];
  ow.forEach((r, i) => {
    const f = { fill: { color: i % 2 ? HEX.blanco : HEX.claro }, fontSize: 15, color: HEX.tinta, valign: "middle" };
    const hecho = r[2] === "Hecho";
    filas.push([
      { text: r[0], options: { ...f, bold: true } }, { text: r[1], options: f },
      { text: (hecho ? "✓ " : "! ") + r[2], options: { ...f, bold: true, align: "center", color: hecho ? HEX.tinta : HEX.rojo } },
    ]);
  });
  s.addTable(filas, { x: 0.6, y: 1.45, w: 12.1, colW: [2.6, 7.4, 2.1], rowH: 0.6, border: { type: "solid", pt: 0.75, color: HEX.borde }, margin: [0, 0.12, 0, 0.12] });
  await circuloIcono(s, "FaScaleBalanced", 0.6, 5.95, 0.5, C.accent3, HEX.rojo);
  T(s, "Estas medidas también ayudan a cumplir la Ley 21.459: protegen contra el acceso ilícito y el daño a datos.", { x: 1.25, y: 5.93, w: 11.4, h: 0.55, fontSize: 15, valign: "middle" });

  // ===== 14. Conclusiones =====
  pres.addSection({ title: "Cierre" });
  s = pres.addSlide({ masterName: "CIERRE", sectionTitle: "Cierre" });
  s.addText("Conclusiones", { placeholder: "title" });
  const conc = [
    ["FaCircleCheck", "El prototipo cumple los requisitos de la segunda evaluación: cada caso de uso tiene su pantalla y sus pruebas."],
    ["FaHandshake", "Las decisiones que tomamos (Scrum, UML y el servidor en AWS) nos resultaron bien."],
    ["FaShieldHalved", "Detectamos mejoras de seguridad que dejamos planificadas, como activar HTTPS."],
    ["FaArrowRight", "A futuro: completar Vecinos, Seguimiento, Reportes y Auditoría, que hoy son plantillas."],
  ];
  for (let i = 0; i < conc.length; i++) {
    const y = 1.75 + i * 1.05;
    await circuloIcono(s, conc[i][0], 0.7, y, 0.62, C.background1, HEX.rojo);
    T(s, conc[i][1], { x: 1.6, y: y - 0.05, w: 10.6, h: 0.75, fontSize: 18, color: C.background1, valign: "middle" });
  }
  T(s, "¡Gracias! ¿Preguntas?", { x: 0.7, y: 6.25, w: 9, h: 0.7, fontSize: 30, bold: true, color: C.background1, valign: "middle" });

  // ===== 15. Referencias =====
  s = pres.addSlide({ masterName: "REFERENCIAS", sectionTitle: "Cierre" });
  s.addText("Referencias", { placeholder: "title" });
  const refs = [
    "Association for Computing Machinery. (2018). Código de ética y conducta profesional de la ACM. https://www.acm.org/about-acm/code-of-ethics-in-spanish",
    "IEEE. (s. f.). Código de ética del IEEE. https://www.ieee.org/about/corporate/governance/p7-8.html",
    "INACAP. (s. f.). Implementación, pruebas y calidad de software.",
    "International Organization for Standardization. (2022). ISO/IEC 27001:2022. Information security management systems.",
    "ISO/IEC/IEEE. (2017). ISO/IEC/IEEE 12207:2017. Software life cycle processes.",
    "Ley N.º 19.628 sobre protección de la vida privada. Diario Oficial de la República de Chile.",
    "Ley N.º 21.459 que establece normas sobre delitos informáticos. https://www.bcn.cl/leychile/navegar?idNorma=1177492",
    "Ley N.º 21.719 que regula la protección y el tratamiento de los datos personales (2024).",
    "OWASP Foundation. (2025). OWASP Top 10:2025. https://owasp.org/Top10/2025/",
    "Pressman, R. y Maxim, B. (2020). Software engineering: A practitioner’s approach (9.ª ed.). McGraw-Hill.",
    "Schwaber, K. y Sutherland, J. (2020). La Guía Scrum. https://scrumguides.org/",
    "Sommerville, I. (2019). Software engineering (10.ª ed.). Pearson.",
  ];
  s.addText(refs.map((r, i) => ({ text: r, options: { breakLine: i < refs.length - 1 } })), { placeholder: "body", paraSpaceAfter: 6 });

  await pres.writeFile({ fileName: SALIDA });
  await applyTheme(SALIDA, THEME);
  console.log("OK", SALIDA);
})().catch(e => { console.error(e); process.exit(1); });
