"""
Pruebas de interfaz en navegador (Playwright + Chromium) con capturas de evidencia.

Requisitos: servidor del SGR en ejecución con datos de prueba y correo por
consola redirigido a un archivo de log (para leer el código de recuperación).

    python manage.py cargar_datos_demo
    python manage.py runserver 127.0.0.1:8000 > servidor.log 2>&1 &
    python pruebas/e2e/pruebas_interfaz.py --url http://127.0.0.1:8000 --log servidor.log

Salidas: docs/evidencias/*.png y docs/pruebas/resultados_interfaz.md
Nota: el flujo de recuperación cambia la clave de «funcionario»; vuelva a
ejecutar `cargar_datos_demo` para restaurarla.
"""
import argparse
import os
import re
import time
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = Path(__file__).resolve().parents[2]
EVID = BASE / "docs" / "evidencias"
CLAVE = os.environ.get("SGR_CLAVE_DEMO", "Serena.2026")
NUEVA = "Nueva#Clave2026"
resultados = []


def caso(id_, descripcion):
    def deco(fn):
        def run(ctx):
            inicio = time.time()
            try:
                evidencia = fn(ctx) or ""
                resultados.append((id_, descripcion, "Aprobada", evidencia, f"{time.time() - inicio:.1f}s"))
            except Exception as e:  # noqa: BLE001
                nombre = f"{id_}_fallo.png"
                try:
                    ctx["pg"].screenshot(path=str(EVID / nombre))
                except Exception:  # noqa: BLE001
                    pass
                resultados.append((id_, descripcion, f"Fallida: {e}".split("\n")[0][:180], nombre, ""))
        run.id = id_
        return run
    return deco


def captura(pg, nombre, completa=False):
    pg.screenshot(path=str(EVID / nombre), full_page=completa)
    return nombre


def swal(pg):
    pg.wait_for_selector(".swal2-popup", state="visible", timeout=5000)
    return pg.inner_text(".swal2-title") + " — " + pg.inner_text(".swal2-html-container")


def cerrar_swal(pg):
    pg.click(".swal2-confirm")
    pg.wait_for_selector(".swal2-popup", state="hidden", timeout=5000)


def entrar(pg, url, usuario, clave=CLAVE):
    pg.goto(url + "/cuenta/ingresar/")
    pg.fill("#id_identificador", usuario)
    pg.fill("#id_clave", clave)
    pg.click("form button[type=submit]")
    pg.wait_for_url(url + "/")
    texto = swal(pg)
    cerrar_swal(pg)
    return texto


def salir(pg):
    pg.click(".cabecera__usuario button[type=submit]")
    swal(pg)
    pg.click(".swal2-confirm")
    pg.wait_for_url(re.compile(".*/cuenta/ingresar/.*"))
    swal(pg)
    cerrar_swal(pg)


@caso("UI-01", "Login incorrecto muestra SweetAlert2 de error y mensaje genérico")
def ui_login_incorrecto(c):
    pg, url = c["pg"], c["url"]
    pg.goto(url + "/cuenta/ingresar/")
    captura(pg, "01_login.png")
    pg.fill("#id_identificador", "funcionario")
    pg.fill("#id_clave", "Incorrecta.1")
    pg.click("form button[type=submit]")
    texto = swal(pg)
    assert "Datos inválidos" in texto and "incorrectos" in texto, texto
    captura(pg, "02_login_incorrecto_swal.png")
    cerrar_swal(pg)
    return "02_login_incorrecto_swal.png"


@caso("UI-02", "Login con campos vacíos se valida en la interfaz con SweetAlert2")
def ui_login_vacio(c):
    pg, url = c["pg"], c["url"]
    pg.goto(url + "/cuenta/ingresar/")
    pg.click("form button[type=submit]")
    texto = swal(pg)
    assert "Complete los datos requeridos" in texto, texto
    captura(pg, "03_login_vacio_swal.png")
    cerrar_swal(pg)
    return "03_login_vacio_swal.png"


@caso("UI-03", "Cada rol ve solo sus menús (Superadministrador, Coordinador, Delegado municipal, Funcionario)")
def ui_menus_por_rol(c):
    pg, url = c["pg"], c["url"]
    esperado = {"superadmin": ("Auditoría", None), "coordinador": ("Usuarios", "Auditoría"),
                "delegado": ("Reportes", "Roles"), "funcionario": ("Atenciones", "Usuarios")}
    for usuario, (debe, no_debe) in esperado.items():
        entrar(pg, url, usuario)
        menu = pg.inner_text("#menu")
        assert debe in menu, f"{usuario} no ve {debe}"
        if no_debe:
            assert no_debe not in menu, f"{usuario} ve {no_debe}"
        captura(pg, f"04_inicio_{usuario}.png", completa=True)
        salir(pg)
    return "04_inicio_*.png"


@caso("UI-04", "Recuperación: solicitar, pegar código de 6 dígitos, requisitos de clave y confirmación SweetAlert2")
def ui_recuperacion(c):
    pg, url, log = c["pg"], c["url"], c["log"]
    pg.goto(url + "/cuenta/recuperar/")
    captura(pg, "05_recuperar.png")
    pg.fill("#id_correo", "funcionario@sgr.test")
    pg.click("form button[type=submit]")
    pg.wait_for_url(re.compile(".*/recuperar/validar/"))
    texto = swal(pg)
    assert "Si el correo corresponde" in texto, texto
    cerrar_swal(pg)
    time.sleep(0.5)
    codigos = re.findall(r"Su c=C3=B3digo de verificaci=C3=B3n es: (\d{6})|Su código de verificación es: (\d{6})",
                         Path(log).read_text(encoding="utf-8", errors="ignore"))
    codigo = [a or b for a, b in codigos][-1]
    assert pg.is_disabled("#btn-reenviar"), "El reenvío debería estar deshabilitado durante la espera"
    captura(pg, "06_validar_codigo.png")
    pg.focus("[data-otp] >> nth=0")
    pg.evaluate("""(codigo) => {
        const dt = new DataTransfer(); dt.setData('text', codigo);
        document.querySelector('[data-otp]').dispatchEvent(new ClipboardEvent('paste', {clipboardData: dt, bubbles: true}));
    }""", codigo)
    valores = pg.eval_on_selector_all("[data-otp]", "els => els.map(e => e.value).join('')")
    assert valores == codigo, f"Pegado: {valores} != {codigo}"
    pg.click("#form-codigo button[type=submit]")
    pg.wait_for_url(re.compile(".*/nueva-clave/"))
    cerrar_swal(pg)
    pg.fill("#id_clave1", "debil")
    assert pg.get_attribute("[data-requisito=mayuscula]", "class") == "no"
    pg.fill("#id_clave1", NUEVA)
    pg.fill("#id_clave2", NUEVA)
    assert pg.eval_on_selector_all("#requisitos li.ok", "e => e.length") == 6
    pg.click("[data-ver-clave=id_clave1]")
    assert pg.get_attribute("#id_clave1", "type") == "text"
    assert pg.get_attribute("[data-ver-clave=id_clave1]", "aria-pressed") == "true"
    captura(pg, "07_nueva_clave.png")
    pg.click("#form-clave button[type=submit]")
    pg.wait_for_url(re.compile(".*/cuenta/ingresar/"))
    texto = swal(pg)
    assert "Contraseña actualizada" in texto, texto
    captura(pg, "08_clave_actualizada_swal.png")
    cerrar_swal(pg)
    entrar(pg, url, "funcionario", NUEVA)
    salir(pg)
    return "05..08_*.png"


@caso("UI-05", "Listado: búsqueda, filtros conservados al paginar y exportación a Excel")
def ui_listado(c):
    pg, url = c["pg"], c["url"]
    entrar(pg, url, "coordinador")
    pg.goto(url + "/items/")
    pg.fill("#q", "META")
    pg.select_option("#f-estado", "activo")
    pg.wait_for_url(re.compile(".*estado=activo.*"))
    pg.click(".paginador a:has-text('2')")
    pg.wait_for_url(re.compile(".*pagina=2.*"))
    assert "q=META" in pg.url and "estado=activo" in pg.url, pg.url
    assert pg.input_value("#q") == "META"
    captura(pg, "09_items_filtro_pagina2.png", completa=True)
    with pg.expect_download() as descarga:
        pg.click("a[data-exportar]")
    archivo = descarga.value
    assert archivo.suggested_filename.startswith("items_") and archivo.suggested_filename.endswith(".xlsx")
    pg.goto(url + "/items/?q=zzzz")
    assert "Sin coincidencias" in pg.inner_text(".tabla-contenedor")
    captura(pg, "10_sin_coincidencias.png")
    return "09_items_filtro_pagina2.png, 10_sin_coincidencias.png"


@caso("UI-06", "Eliminar: confirmación SweetAlert2, cancelación sin cambios y rechazo por relaciones")
def ui_eliminar(c):
    pg, url = c["pg"], c["url"]
    pg.goto(url + "/tipos-atencion/")
    pg.click("tbody tr:first-child form[action$='/eliminar/'] button")
    texto = swal(pg)
    assert "no se puede deshacer" in texto, texto
    captura(pg, "11_confirmar_eliminar.png")
    pg.click(".swal2-cancel")
    texto = swal(pg)
    assert "Operación cancelada" in texto, texto
    cerrar_swal(pg)
    pg.click("tbody tr:first-child form[action$='/eliminar/'] button")
    swal(pg)
    pg.click(".swal2-confirm")
    pg.wait_for_load_state()
    texto = swal(pg)
    assert "No se puede eliminar" in texto and "Operación exitosa" not in texto, texto
    captura(pg, "12_eliminar_rechazado_relaciones.png")
    cerrar_swal(pg)
    return "11_confirmar_eliminar.png, 12_eliminar_rechazado_relaciones.png"


@caso("UI-07", "Formulario CRUD: validación de requeridos en la interfaz y error de duplicado del servidor")
def ui_formulario(c):
    pg, url = c["pg"], c["url"]
    pg.goto(url + "/sub-atenciones/nuevo/")
    pg.click("form[data-validar] button[type=submit]")
    texto = swal(pg)
    assert "Complete los datos requeridos" in texto, texto
    captura(pg, "13_validacion_requeridos.png")
    cerrar_swal(pg)
    pg.fill("#id_codigo", "sa01")
    pg.fill("#id_nombre", "Duplicada")
    pg.select_option("#id_tipo", index=1)
    pg.click("form[data-validar] button[type=submit]")
    pg.wait_for_load_state()
    texto = swal(pg)
    assert "Datos inválidos" in texto, texto
    cerrar_swal(pg)
    assert "Ya existe un registro con este código" in pg.inner_text("main form[data-validar]")
    captura(pg, "14_error_duplicado.png", completa=True)
    return "13_validacion_requeridos.png, 14_error_duplicado.png"


@caso("UI-08", "Cambio de delegación advierte cambios sin guardar y actualiza el contexto")
def ui_cambio_delegacion(c):
    pg, url = c["pg"], c["url"]
    pg.goto(url + "/items/nuevo/")
    pg.fill("#id_nombre", "Cambio sin guardar")
    pg.select_option("#selector-delegacion", label="DEL02 | Delegación Las Compañías")
    texto = swal(pg)
    assert "Cambios sin guardar" in texto, texto
    captura(pg, "15_advertencia_cambio_delegacion.png")
    pg.click(".swal2-cancel")
    assert pg.input_value("#selector-delegacion") != "", "selector"
    assert "DEL01" in pg.inner_text("#selector-delegacion option:checked")
    pg.select_option("#selector-delegacion", label="DEL02 | Delegación Las Compañías")
    swal(pg)
    pg.click(".swal2-confirm")
    pg.wait_for_url(url + "/items/")
    texto = swal(pg)
    assert "DEL02" in texto, texto
    cerrar_swal(pg)
    assert "DEL02" in pg.inner_text(".encabezado")
    captura(pg, "16_contexto_del02.png")
    pg.select_option("#selector-delegacion", label="DEL01 | Delegación Centro")
    pg.wait_for_url(url + "/items/")
    cerrar_swal(pg)
    salir(pg)
    return "15_advertencia_cambio_delegacion.png, 16_contexto_del02.png"


@caso("UI-09", "Ingreso de atención: vecino, dependencia Tipo→Sub Atención, doble envío y folio con SweetAlert2")
def ui_atencion(c):
    pg, url = c["pg"], c["url"]
    entrar(pg, url, "delegado")
    pg.goto(url + "/atenciones/nueva/")
    assert pg.is_disabled("#id_subatencion")
    pg.fill("#buscar-vecino", "a")
    pg.type("#buscar-vecino", "n")
    pg.wait_for_selector("#resultados-vecino li button")
    pg.click("#resultados-vecino li button >> nth=0")
    pg.select_option("#id_tipo", label="TA01 · Social")
    pg.wait_for_function("document.querySelector('#id_subatencion').options.length > 1")
    opciones = pg.eval_on_selector_all("#id_subatencion option", "o => o.map(x => x.textContent)")
    assert "Ayuda social" in opciones and "Luminaria pública" not in opciones, opciones
    pg.select_option("#id_subatencion", label="Ayuda social")
    pg.select_option("#id_tipo", label="TA02 · Infraestructura")
    pg.wait_for_function("[...document.querySelector('#id_subatencion').options].some(o => o.textContent === 'Luminaria pública')")
    assert pg.input_value("#id_subatencion") == "", "La sub atención no se limpió al cambiar el tipo"
    pg.select_option("#id_subatencion", label="Luminaria pública")
    pg.fill("#id_descripcion", "Luminaria apagada frente al número 123. Prueba de interfaz.")
    assert "DEL01" in pg.input_value("#delegacion-atencion")
    captura(pg, "17_ingreso_atencion.png", completa=True)
    pg.dblclick("#form-atencion button[type=submit]")
    pg.wait_for_url(re.compile(".*/atenciones/\\d+/"))
    texto = swal(pg)
    assert "Folio: AT-" in texto, texto
    captura(pg, "18_atencion_registrada_folio.png")
    cerrar_swal(pg)
    return "17_ingreso_atencion.png, 18_atencion_registrada_folio.png"


@caso("UI-10", "Módulo pendiente: plantilla navegable que informa función pendiente sin simular éxito")
def ui_pendiente(c):
    pg, url = c["pg"], c["url"]
    pg.goto(url + "/modulo/reportes/")
    pg.click("[data-pendiente] >> nth=0")
    texto = swal(pg)
    assert "Función pendiente" in texto and "No se registró" in texto, texto
    captura(pg, "19_modulo_pendiente.png")
    cerrar_swal(pg)
    return "19_modulo_pendiente.png"


@caso("UI-11", "Acceso por URL a módulo no autorizado muestra 403 con SweetAlert2")
def ui_403(c):
    pg, url = c["pg"], c["url"]
    pg.goto(url + "/roles/")
    texto = swal(pg)
    assert "Acceso no autorizado" in texto, texto
    captura(pg, "20_acceso_denegado_403.png")
    salir_directo(pg, url)
    return "20_acceso_denegado_403.png"


def salir_directo(pg, url):
    pg.goto(url + "/")
    cerrar_swal_si(pg)
    salir(pg)


def cerrar_swal_si(pg):
    if pg.is_visible(".swal2-popup"):
        cerrar_swal(pg)


@caso("UI-12", "Diseño adaptable en pantalla móvil (390 px) con menú desplegable")
def ui_movil(c):
    pg, url = c["pg"], c["url"]
    pg.set_viewport_size({"width": 390, "height": 844})
    entrar(pg, url, "funcionario", NUEVA)
    captura(pg, "21_movil_inicio.png")
    pg.click("[data-alternar-menu]")
    assert pg.get_attribute("[data-alternar-menu]", "aria-expanded") == "true"
    captura(pg, "22_movil_menu.png")
    pg.set_viewport_size({"width": 1366, "height": 850})
    return "21_movil_inicio.png, 22_movil_menu.png"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--log", required=True)
    parser.add_argument("--chromium", default=os.environ.get("CHROMIUM_PATH"))
    parser.add_argument("--entorno", default="", help="Descripción del entorno probado")
    args = parser.parse_args()
    EVID.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        navegador = p.chromium.launch(executable_path=args.chromium) if args.chromium else p.chromium.launch()
        pg = navegador.new_page(viewport={"width": 1366, "height": 850}, locale="es-CL", accept_downloads=True)
        ctx = {"pg": pg, "url": args.url.rstrip("/"), "log": args.log}
        for prueba in [ui_login_incorrecto, ui_login_vacio, ui_menus_por_rol, ui_recuperacion, ui_listado,
                       ui_eliminar, ui_formulario, ui_cambio_delegacion, ui_atencion, ui_pendiente, ui_403,
                       ui_movil]:
            prueba(ctx)
        navegador.close()
    fecha = datetime.now().strftime("%d-%m-%Y %H:%M")
    ok = sum(1 for r in resultados if r[2] == "Aprobada")
    lineas = ["# Resultados de pruebas de interfaz (navegador)", "",
              f"Ejecución: **{fecha}** · URL: `{args.url}` {args.entorno} · Navegador: Chromium (Playwright) · "
              f"Aprobadas: **{ok}/{len(resultados)}**", "",
              "Generado con `python pruebas/e2e/pruebas_interfaz.py`. Capturas en `docs/evidencias/`.", "",
              "| ID | Caso | Estado | Evidencia | Duración |", "|---|---|---|---|---|"]
    lineas += [f"| {a} | {b} | {c} | {d} | {e} |" for a, b, c, d, e in resultados]
    (BASE / "docs" / "pruebas" / "resultados_interfaz.md").write_text("\n".join(lineas) + "\n", encoding="utf-8")
    for r in resultados:
        print(" | ".join(r))
    print(f"{ok}/{len(resultados)} aprobadas")


if __name__ == "__main__":
    main()
