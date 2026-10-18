/* SGR · comportamiento común del template (SweetAlert2, formularios, contexto). */
(function () {
  "use strict";

  var ROJO = "#C41230";
  var GRIS = "#6E6E6E";

  var Alerta = window.Swal ? Swal.mixin({
    confirmButtonColor: ROJO,
    cancelButtonColor: GRIS,
    confirmButtonText: "Aceptar",
    cancelButtonText: "Cancelar",
    reverseButtons: true,
    focusCancel: false
  }) : null;
  window.SGR = { Alerta: Alerta };

  var TITULOS = { success: "Operación exitosa", error: "No se pudo completar", warning: "Atención", info: "Información" };

  function leerJSON(id) {
    var nodo = document.getElementById(id);
    if (!nodo) return null;
    try { return JSON.parse(nodo.textContent); } catch (e) { return null; }
  }

  // --- 1. Mensajes del servidor -> SweetAlert2 (en cola) ---------------------
  async function mostrarMensajes() {
    if (!Alerta) return;
    var mensajes = leerJSON("mensajes-sgr") || [];
    var errores = leerJSON("errores-formulario");
    for (var i = 0; i < mensajes.length; i++) {
      var m = mensajes[i];
      var nivel = (m.nivel || "info").split(" ")[0];
      if (!TITULOS[nivel]) nivel = "info";
      await Alerta.fire({
        icon: nivel, title: TITULOS[nivel], text: m.texto,
        timer: nivel === "success" ? 3500 : undefined, timerProgressBar: nivel === "success"
      });
    }
    if (errores) {
      var html = errores.generales.length
        ? errores.generales.map(function (t) { return "<p>" + escapar(t) + "</p>"; }).join("")
        : "<p>Revise los campos marcados en rojo y corrija los datos indicados.</p>";
      await Alerta.fire({ icon: "error", title: "Datos inválidos", html: html });
      var primero = document.querySelector(".con-error input, .con-error select, .con-error textarea");
      if (primero) primero.focus();
    }
  }

  function escapar(t) {
    var d = document.createElement("div"); d.textContent = t; return d.innerHTML;
  }

  // --- 2. Cambios sin guardar ------------------------------------------------
  var hayCambios = false;
  document.querySelectorAll("form[data-proteger]").forEach(function (f) {
    f.addEventListener("input", function () { hayCambios = true; });
    f.addEventListener("change", function () { hayCambios = true; });
    f.addEventListener("submit", function () { hayCambios = false; });
  });
  window.addEventListener("beforeunload", function (e) {
    if (hayCambios) { e.preventDefault(); e.returnValue = ""; }
  });
  window.SGR.hayCambios = function () { return hayCambios; };

  function confirmarSalida(mensaje) {
    if (!hayCambios || !Alerta) return Promise.resolve(true);
    return Alerta.fire({
      icon: "warning", title: "Cambios sin guardar", text: mensaje,
      showCancelButton: true, confirmButtonText: "Descartar cambios", cancelButtonText: "Seguir editando"
    }).then(function (r) { if (r.isConfirmed) hayCambios = false; return r.isConfirmed; });
  }

  document.querySelectorAll("[data-cancelar]").forEach(function (a) {
    a.addEventListener("click", function (e) {
      if (!hayCambios) return;
      e.preventDefault();
      confirmarSalida("Si cancela, los datos ingresados no se guardarán.").then(function (ok) {
        if (ok) window.location.href = a.href;
      });
    });
  });

  // --- 3. Cambio de delegación activa ----------------------------------------
  var formDelegacion = document.querySelector("form[data-cambio-delegacion]");
  if (formDelegacion) {
    var selector = formDelegacion.querySelector("select");
    var original = selector.value;
    selector.addEventListener("change", function () {
      var texto = selector.options[selector.selectedIndex].text;
      confirmarSalida("Al cambiar a " + texto + " se perderán los cambios no guardados de esta pantalla.")
        .then(function (ok) {
          if (!ok) { selector.value = original; return; }
          if (Alerta) Alerta.fire({ title: "Cambiando de delegación…", text: texto, allowOutsideClick: false,
            didOpen: function () { Swal.showLoading(); } });
          formDelegacion.submit();
        });
    });
  }

  // --- 4. Confirmaciones (eliminar, desactivar, cerrar sesión) ---------------
  document.querySelectorAll("form[data-confirmar]").forEach(function (f) {
    f.addEventListener("submit", function (e) {
      if (f.dataset.confirmado === "1" || !Alerta) return;
      e.preventDefault();
      Alerta.fire({
        icon: f.dataset.confirmarIcono || "warning",
        title: f.dataset.confirmarTitulo || "Confirmar acción",
        text: f.dataset.confirmar,
        showCancelButton: true,
        confirmButtonText: f.dataset.confirmarBoton || "Confirmar"
      }).then(function (r) {
        if (r.isConfirmed) {
          f.dataset.confirmado = "1";
          f.requestSubmit ? f.requestSubmit() : f.submit();
        } else if (r.dismiss === Swal.DismissReason.cancel && f.dataset.cancelado) {
          Alerta.fire({ icon: "info", title: "Operación cancelada", text: f.dataset.cancelado, timer: 2200 });
        }
      });
    });
  });

  // --- 5. Prevención de doble envío -------------------------------------------
  document.querySelectorAll("form[data-un-envio]").forEach(function (f) {
    f.addEventListener("submit", function (e) {
      if (f.dataset.enviando === "1") { e.preventDefault(); return; }
      if (!f.checkValidity()) return;
      f.dataset.enviando = "1";
      f.querySelectorAll("button[type=submit]").forEach(function (b) {
        b.disabled = true; b.dataset.texto = b.innerHTML; b.innerHTML = '<span class="spinner" style="width:16px;height:16px;border-width:2px"></span> Guardando…';
      });
    });
  });
  // Validación nativa: avisar con SweetAlert2 antes de enviar.
  document.querySelectorAll("form[data-validar]").forEach(function (f) {
    f.setAttribute("novalidate", "");
    f.addEventListener("submit", function (e) {
      if (f.checkValidity()) return;
      e.preventDefault(); e.stopImmediatePropagation();
      var invalidos = Array.prototype.slice.call(f.querySelectorAll(":invalid")).filter(function (c) { return c.name; });
      var nombres = invalidos.map(function (c) {
        var l = f.querySelector('label[for="' + c.id + '"]');
        var n = l ? l.textContent.replace("*", "").trim() : c.name;
        return "<li><strong>" + escapar(n) + "</strong>: " + escapar(c.validationMessage) + "</li>";
      });
      invalidos.forEach(function (c) { var w = c.closest(".campo"); if (w) w.classList.add("con-error"); });
      if (Alerta) Alerta.fire({ icon: "error", title: "Complete los datos requeridos",
        html: '<ul style="text-align:left;margin:0;padding-left:18px">' + nombres.join("") + "</ul>" });
      if (invalidos[0]) invalidos[0].focus();
    }, true);
  });

  // --- 6. Búsqueda: estado de carga y filtros --------------------------------
  document.querySelectorAll("form[data-busqueda]").forEach(function (f) {
    f.addEventListener("submit", function () {
      var t = document.querySelector(".tabla-contenedor"); if (t) t.classList.add("cargando");
    });
    f.querySelectorAll("select").forEach(function (s) {
      s.addEventListener("change", function () { f.requestSubmit ? f.requestSubmit() : f.submit(); });
    });
  });
  document.querySelectorAll(".paginador a").forEach(function (a) {
    a.addEventListener("click", function () {
      var t = document.querySelector(".tabla-contenedor"); if (t) t.classList.add("cargando");
    });
  });
  document.querySelectorAll("a[data-exportar]").forEach(function (a) {
    a.addEventListener("click", function () {
      if (Alerta) Alerta.fire({ toast: true, position: "top-end", icon: "info", title: "Generando archivo Excel…",
        text: a.dataset.exportar, showConfirmButton: false, timer: 2500 });
    });
  });

  // --- 7. Mostrar / ocultar contraseña (accesible) ---------------------------
  document.querySelectorAll("[data-ver-clave]").forEach(function (b) {
    b.addEventListener("click", function () {
      var input = document.getElementById(b.dataset.verClave);
      var mostrar = input.type === "password";
      input.type = mostrar ? "text" : "password";
      b.setAttribute("aria-pressed", mostrar ? "true" : "false");
      b.setAttribute("aria-label", mostrar ? "Ocultar contraseña" : "Mostrar contraseña");
      b.querySelector("use").setAttribute("href", mostrar ? "#i-ojo-no" : "#i-ojo");
    });
  });

  // --- 8. Menú adaptable -----------------------------------------------------
  var botonMenu = document.querySelector("[data-alternar-menu]");
  if (botonMenu) {
    botonMenu.addEventListener("click", function () {
      var menu = document.getElementById("menu");
      var abierto = menu.classList.toggle("abierto");
      botonMenu.setAttribute("aria-expanded", abierto ? "true" : "false");
    });
  }

  mostrarMensajes();
})();
