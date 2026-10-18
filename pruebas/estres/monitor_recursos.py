"""
Registra CPU y memoria del servidor durante una prueba de estrés.

    python pruebas/estres/monitor_recursos.py --salida docs/pruebas/estres/recursos.csv --segundos 300

En AWS puede ejecutarse en la instancia EC2 (o usar CloudWatch). Mide el uso
total del sistema y el de los procesos gunicorn.
"""
import argparse
import csv
import time

import psutil


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--salida", required=True)
    parser.add_argument("--segundos", type=int, default=300)
    parser.add_argument("--intervalo", type=float, default=5)
    parser.add_argument("--proceso", default="gunicorn")
    args = parser.parse_args()
    fin = time.time() + args.segundos
    with open(args.salida, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["marca", "cpu_sistema_pct", "memoria_sistema_pct", "cpu_app_pct", "memoria_app_mb"])
        psutil.cpu_percent()
        while time.time() < fin:
            procesos = [p for p in psutil.process_iter(["name", "cmdline"])
                        if args.proceso in " ".join(p.info["cmdline"] or [])]
            for p in procesos:
                try:
                    p.cpu_percent()
                except psutil.Error:
                    pass
            time.sleep(args.intervalo)
            cpu_app, mem_app = 0.0, 0.0
            for p in procesos:
                try:
                    cpu_app += p.cpu_percent()
                    mem_app += p.memory_info().rss / 1_048_576
                except psutil.Error:
                    pass
            w.writerow([time.strftime("%H:%M:%S"), psutil.cpu_percent(), psutil.virtual_memory().percent,
                        round(cpu_app, 1), round(mem_app, 1)])
            f.flush()


if __name__ == "__main__":
    main()
