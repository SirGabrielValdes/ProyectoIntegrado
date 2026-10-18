/* Ingreso de atención: búsqueda de vecino y dependencia Tipo -> Sub Atención. */
(function () {
  "use strict";
  var form = document.getElementById("form-atencion");
  if (!form) return;

  // --- Tipo de Atención -> Sub Atención (solo activas del tipo elegido) ------
  var tipo = document.getElementById("id_tipo");
  var sub = document.getElementById("id_subatencion");

  function cargarSub(conservar) {
    var previo = conservar ? sub.value : "";
    if (!tipo.value) {
      sub.innerHTML = '<option value="">Seleccione primero un tipo…</option>';
      sub.disabled = true;
      return Promise.resolve();
    }
    sub.disabled = true;
    sub.innerHTML = '<option value="">Cargando…</option>';
    return fetch(form.dataset.urlSub + "?tipo=" + encodeURIComponent(tipo.value), { headers: { "X-Requested-With": "fetch" } })
      .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
      .then(function (datos) {
        var ops = ['<option value="">' + (datos.resultados.length ? "Seleccione una sub atención…" : "Sin sub atenciones activas para este tipo") + "</option>"];
        datos.resultados.forEach(function (s) {
          var o = document.createElement("option"); o.value = s.id; o.textContent = s.texto;
          ops.push(o.outerHTML);
        });
        sub.innerHTML = ops.join("");
        // Si la sub atención anterior ya no es válida para el nuevo tipo, queda limpia.
        var valido = datos.resultados.some(function (s) { return String(s.id) === previo; });
        sub.value = valido ? previo : "";
        sub.disabled = datos.resultados.length === 0;
      })
      .catch(function () {
        sub.innerHTML = '<option value="">No fue posible cargar las sub atenciones</option>';
        window.SGR.Alerta.fire({ icon: "error", title: "Error de servidor", text: "No fue posible cargar las sub atenciones. Intente nuevamente." });
      });
  }
  tipo.addEventListener("change", function () { cargarSub(false); });
  cargarSub(true);

  // --- Modo de identificación del vecino -------------------------------------
  var bloqueExistente = document.getElementById("bloque-existente");
  var bloqueNuevo = document.getElementById("bloque-nuevo");
  var radios = form.querySelectorAll('input[name="modo_vecino"]');
  function modo() {
    var m = form.querySelector('input[name="modo_vecino"]:checked');
    var nuevo = m && m.value === "nuevo";
    bloqueNuevo.hidden = !nuevo;
    bloqueExistente.hidden = nuevo;
    document.getElementById("id_rut").required = nuevo;
    document.getElementById("id_nombre").required = nuevo;
  }
  radios.forEach(function (r) { r.addEventListener("change", modo); });
  modo();

  // --- Búsqueda de vecino ----------------------------------------------------
  var buscador = document.getElementById("buscar-vecino");
  var resultados = document.getElementById("resultados-vecino");
  var oculto = document.getElementById("id_vecino");
  var elegido = document.getElementById("vecino-elegido");
  var contenedorBuscador = document.getElementById("vecino-buscador");
  var temporizador = null;

  function elegir(id, texto) {
    oculto.value = id;
    document.getElementById("vecino-texto").textContent = texto;
    elegido.hidden = false; contenedorBuscador.hidden = true; resultados.hidden = true;
    form.dispatchEvent(new Event("change"));
  }
  document.getElementById("vecino-quitar").addEventListener("click", function () {
    oculto.value = ""; elegido.hidden = true; contenedorBuscador.hidden = false; buscador.value = ""; buscador.focus();
  });
  buscador.addEventListener("input", function () {
    clearTimeout(temporizador);
    var q = buscador.value.trim();
    if (q.length < 2) { resultados.hidden = true; return; }
    temporizador = setTimeout(function () {
      fetch(form.dataset.urlVecinos + "?q=" + encodeURIComponent(q))
        .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
        .then(function (datos) {
          resultados.innerHTML = "";
          if (!datos.resultados.length) {
            var li = document.createElement("li");
            li.innerHTML = '<span style="display:block;padding:9px 12px;color:#6E6E6E">Sin coincidencias. Puede usar «Registrar nuevo vecino».</span>';
            resultados.appendChild(li);
          }
          datos.resultados.forEach(function (v) {
            var li = document.createElement("li");
            var b = document.createElement("button"); b.type = "button"; b.textContent = v.texto;
            b.addEventListener("click", function () { elegir(v.id, v.texto); });
            li.appendChild(b); resultados.appendChild(li);
          });
          resultados.hidden = false;
        })
        .catch(function () {
          window.SGR.Alerta.fire({ icon: "error", title: "Error de servidor", text: "No fue posible buscar vecinos." });
        });
    }, 300);
  });

  // Formato visual del RUT.
  var rut = document.getElementById("id_rut");
  rut.addEventListener("blur", function () {
    var limpio = rut.value.replace(/[^0-9kK]/g, "").toUpperCase();
    if (limpio.length < 2) return;
    var cuerpo = limpio.slice(0, -1).replace(/\B(?=(\d{3})+(?!\d))/g, ".");
    rut.value = cuerpo + "-" + limpio.slice(-1);
  });

  // Validación previa del vecino antes del envío.
  form.addEventListener("submit", function (e) {
    var m = form.querySelector('input[name="modo_vecino"]:checked');
    if (m && m.value === "existente" && !oculto.value) {
      e.preventDefault(); e.stopImmediatePropagation();
      window.SGR.Alerta.fire({ icon: "error", title: "Falta el solicitante", text: "Busque y seleccione al vecino, o registre uno nuevo." });
      buscador.focus();
    }
  }, true);
})();
