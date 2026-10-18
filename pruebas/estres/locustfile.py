"""
Pruebas de estrés del SGR con Locust.

Escenarios sobre operaciones integradas (con base de datos):
  - Funcionario: inicio, listado y búsqueda de atenciones, sub atenciones dependientes
    y registro de atenciones (escritura).
  - Coordinador: listados con búsqueda/filtros/paginación de mantenedores y exportación a Excel.
  - Acceso: carga de login y autenticación.

La carga aumenta por etapas (LoadTestShape) hasta observar degradación o
alcanzar el límite seguro del entorno. Etapas configurables con
SGR_ETAPAS="usuarios:segundos,..." (por defecto 10:60,25:60,50:60,100:60,150:60).

Ejecución (ver docs/pruebas/plan_pruebas_estres.md):
    locust -f pruebas/estres/locustfile.py --host https://<url-aws> --headless \
           --csv docs/pruebas/estres/resultado --html docs/pruebas/estres/reporte.html
"""
import os
import random
import re

from locust import HttpUser, LoadTestShape, between, task

CLAVE = os.environ.get("SGR_CLAVE_DEMO", "Serena.2026")
RE_CSRF = re.compile(r'name="csrfmiddlewaretoken" value="([^"]+)"')
RE_TOKEN = re.compile(r'name="token" value="([^"]+)"')
RE_VECINO = re.compile(r'"id": (\d+)')


def ingresar(usuario, nombre):
    r = usuario.client.get("/cuenta/ingresar/", name="GET login")
    csrf = RE_CSRF.search(r.text).group(1)
    with usuario.client.post("/cuenta/ingresar/", {"csrfmiddlewaretoken": csrf, "identificador": nombre,
                                                   "clave": CLAVE},
                             headers={"Referer": usuario.host + "/cuenta/ingresar/"},
                             name="POST login", allow_redirects=False, catch_response=True) as resp:
        if resp.status_code != 302:
            resp.failure(f"Login rechazado ({resp.status_code})")


class Funcionario(HttpUser):
    weight = 3
    wait_time = between(1, 3)

    def on_start(self):
        ingresar(self, random.choice(["funcionario", "funcionario2", "delegado"]))

    @task(3)
    def inicio(self):
        self.client.get("/", name="Inicio")

    @task(4)
    def listar_atenciones(self):
        q = random.choice(["", "social", "luminaria", "a"])
        self.client.get(f"/atenciones/?q={q}&pagina={random.randint(1, 3)}", name="Atenciones: listar/buscar")

    @task(2)
    def subatenciones(self):
        self.client.get(f"/atenciones/api/subatenciones/?tipo={random.randint(1, 5)}", name="API sub atenciones")

    @task(1)
    def registrar_atencion(self):
        r = self.client.get("/atenciones/nueva/", name="Atención: formulario")
        csrf, token = RE_CSRF.search(r.text), RE_TOKEN.search(r.text)
        vecinos = self.client.get("/atenciones/api/vecinos/?q=an", name="API vecinos").text
        ids = RE_VECINO.findall(vecinos)
        if not (csrf and token and ids):
            return
        tipo = random.randint(1, 5)
        subs = RE_VECINO.findall(self.client.get(f"/atenciones/api/subatenciones/?tipo={tipo}",
                                                 name="API sub atenciones").text)
        if not subs:
            return
        with self.client.post("/atenciones/nueva/", {
            "csrfmiddlewaretoken": csrf.group(1), "token": token.group(1), "modo_vecino": "existente",
            "vecino": random.choice(ids), "tipo": tipo, "subatencion": random.choice(subs),
            "descripcion": "Atención generada por prueba de estrés (datos ficticios).",
        }, headers={"Referer": self.host + "/atenciones/nueva/"}, name="Atención: registrar",
                allow_redirects=False, catch_response=True) as resp:
            if resp.status_code != 302:
                resp.failure(f"No se registró ({resp.status_code})")


class Coordinador(HttpUser):
    weight = 2
    wait_time = between(1, 3)

    def on_start(self):
        ingresar(self, "coordinador")

    @task(4)
    def listar_items(self):
        self.client.get(f"/items/?q=meta&estado=activo&pagina={random.randint(1, 3)}", name="Ítems: buscar/paginar")

    @task(3)
    def listar_usuarios(self):
        self.client.get("/usuarios/?q=a", name="Usuarios: buscar")

    @task(2)
    def listar_subatenciones(self):
        self.client.get(f"/sub-atenciones/?tipo={random.randint(1, 5)}", name="Sub atenciones: filtrar")

    @task(1)
    def exportar(self):
        self.client.get("/atenciones/exportar/", name="Atenciones: exportar Excel")


class Acceso(HttpUser):
    weight = 1
    wait_time = between(2, 5)

    @task
    def login_logout(self):
        ingresar(self, "superadmin")
        r = self.client.get("/", name="Inicio")
        csrf = RE_CSRF.search(r.text)
        if csrf:
            self.client.post("/cuenta/salir/", {"csrfmiddlewaretoken": csrf.group(1)},
                             headers={"Referer": self.host + "/"}, name="POST logout", allow_redirects=False)


class CargaProgresiva(LoadTestShape):
    """Aumenta usuarios concurrentes por etapas (usuarios:segundos)."""

    etapas = [tuple(map(int, e.split(":"))) for e in
              os.environ.get("SGR_ETAPAS", "10:60,25:60,50:60,100:60,150:60").split(",")]

    def tick(self):
        transcurrido = self.get_run_time()
        acumulado = 0
        for usuarios, duracion in self.etapas:
            acumulado += duracion
            if transcurrido < acumulado:
                return usuarios, max(1, usuarios // 5)
        return None
