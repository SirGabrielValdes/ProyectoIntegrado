"""
Resume los CSV de Locust y del monitor de recursos en un informe Markdown.

    python pruebas/estres/resumir.py --prefijo docs/pruebas/estres/resultado \
        --recursos docs/pruebas/estres/recursos.csv --entorno "AWS EC2 t3.small + RDS MySQL" \
        --salida docs/pruebas/estres/informe.md
"""
import argparse
import csv
from pathlib import Path

UMBRAL_P95_MS = 1000
UMBRAL_ERRORES_PCT = 1.0


def leer(ruta):
    with open(ruta, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--prefijo", required=True)
    parser.add_argument("--recursos")
    parser.add_argument("--entorno", required=True)
    parser.add_argument("--salida", required=True)
    parser.add_argument("--notas", default="")
    args = parser.parse_args()

    stats = leer(f"{args.prefijo}_stats.csv")
    historia = leer(f"{args.prefijo}_stats_history.csv")
    total = next(r for r in stats if r["Name"] == "Aggregated")
    lineas = ["# Informe de prueba de estrés", "", f"- **Entorno:** {args.entorno}",
              "- **Herramienta:** Locust (`pruebas/estres/locustfile.py`), carga progresiva por etapas",
              f"- **Solicitudes totales:** {total['Request Count']} · **Fallidas:** {total['Failure Count']}",
              f"- **Solicitudes por segundo (promedio):** {float(total['Requests/s']):.1f}",
              f"- **Latencia promedio:** {float(total['Average Response Time']):.0f} ms · "
              f"**p95:** {total['95%']} ms · **máxima:** {float(total['Max Response Time']):.0f} ms",
              f"- **Umbrales de aceptación:** p95 ≤ {UMBRAL_P95_MS} ms y errores ≤ {UMBRAL_ERRORES_PCT} % por etapa",
              ""]
    if args.notas:
        lineas += [args.notas, ""]

    # Evolución por nivel de concurrencia (última muestra de cada etapa).
    etapas = {}
    for fila in historia:
        if fila["Name"] != "Aggregated":
            continue
        usuarios = int(fila["User Count"])
        etapas.setdefault(usuarios, []).append(fila)
    lineas += ["## Resultados por nivel de concurrencia", "",
               "| Usuarios | Solicitudes/s | Latencia prom. (ms) | p95 (ms) | Errores acumulados (%) | ¿Cumple? |",
               "|---|---|---|---|---|---|"]
    for usuarios in sorted(etapas):
        filas = [f for f in etapas[usuarios] if f["Total Request Count"] not in ("0", "")]
        if not filas:
            continue
        ultima = filas[-1]
        rps = sum(float(f["Requests/s"]) for f in filas) / len(filas)
        p95 = max(int(float(f["95%"])) for f in filas if f["95%"] not in ("N/A", ""))
        prom = float(ultima["Total Average Response Time"])
        tot = int(ultima["Total Request Count"]) or 1
        err = 100 * int(ultima["Total Failure Count"]) / tot
        cumple = "Sí" if p95 <= UMBRAL_P95_MS and err <= UMBRAL_ERRORES_PCT else "No (degradación)"
        lineas.append(f"| {usuarios} | {rps:.1f} | {prom:.0f} | {p95} | {err:.2f} | {cumple} |")

    lineas += ["", "## Resultados por operación", "",
               "| Operación | Solicitudes | Fallidas | Prom. (ms) | p95 (ms) | Máx. (ms) | Solic./s |",
               "|---|---|---|---|---|---|---|"]
    for r in stats:
        if r["Name"] == "Aggregated":
            continue
        lineas.append(f"| {r['Type']} {r['Name']} | {r['Request Count']} | {r['Failure Count']} | "
                      f"{float(r['Average Response Time']):.0f} | {r['95%']} | {float(r['Max Response Time']):.0f} | "
                      f"{float(r['Requests/s']):.1f} |")

    fallas = Path(f"{args.prefijo}_failures.csv")
    if fallas.exists():
        filas = leer(fallas)
        if filas:
            lineas += ["", "## Errores registrados", "", "| Operación | Error | Ocurrencias |", "|---|---|---|"]
            for f in filas:
                lineas.append(f"| {f['Method']} {f['Name']} | {f['Error'][:120]} | {f['Occurrences']} |")

    if args.recursos and Path(args.recursos).exists():
        rec = leer(args.recursos)
        if rec:
            cpu = [float(r["cpu_sistema_pct"]) for r in rec]
            mem = [float(r["memoria_app_mb"]) for r in rec]
            lineas += ["", "## CPU y memoria", "",
                       f"- CPU del sistema: promedio {sum(cpu) / len(cpu):.0f} %, máximo {max(cpu):.0f} %",
                       f"- Memoria de la aplicación (gunicorn): promedio {sum(mem) / len(mem):.0f} MB, "
                       f"máximo {max(mem):.0f} MB", f"- Muestras: {len(rec)} (archivo `{args.recursos}`)"]
    Path(args.salida).write_text("\n".join(lineas) + "\n", encoding="utf-8")
    print("\n".join(lineas))


if __name__ == "__main__":
    main()
