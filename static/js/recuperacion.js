/* Recuperación de contraseña: casillas del código, temporizadores y requisitos de clave. */
(function () {
  "use strict";

  // --- Código de 6 dígitos ---------------------------------------------------
  var casillas = Array.prototype.slice.call(document.querySelectorAll("[data-otp]"));
  var oculto = document.getElementById("codigo");
  var formCodigo = document.getElementById("form-codigo");

  function sincronizar() {
    oculto.value = casillas.map(function (c) { return c.value; }).join("");
  }
  function repartir(texto, desde) {
    var digitos = (texto || "").replace(/\D/g, "").slice(0, 6 - desde).split("");
    digitos.forEach(function (d, i) { casillas[desde + i].value = d; });
    var siguiente = Math.min(desde + digitos.length, 5);
    casillas[siguiente].focus();
    sincronizar();
  }

  casillas.forEach(function (c, i) {
    c.addEventListener("input", function () {
      if (c.value.length > 1) { repartir(c.value, i); return; }
      c.value = c.value.replace(/\D/g, "");
      if (c.value && i < 5) casillas[i + 1].focus();
      sincronizar();
    });
    c.addEventListener("keydown", function (e) {
      if (e.key === "Backspace" && !c.value && i > 0) { casillas[i - 1].focus(); casillas[i - 1].value = ""; e.preventDefault(); sincronizar(); }
      else if (e.key === "ArrowLeft" && i > 0) { casillas[i - 1].focus(); e.preventDefault(); }
      else if (e.key === "ArrowRight" && i < 5) { casillas[i + 1].focus(); e.preventDefault(); }
      else if (e.key === "Home") { casillas[0].focus(); e.preventDefault(); }
      else if (e.key === "End") { casillas[5].focus(); e.preventDefault(); }
    });
    c.addEventListener("paste", function (e) {
      e.preventDefault();
      repartir((e.clipboardData || window.clipboardData).getData("text"), i);
    });
    c.addEventListener("focus", function () { c.select(); });
  });

  if (formCodigo) {
    formCodigo.addEventListener("submit", function (e) {
      sincronizar();
      if (!/^\d{6}$/.test(oculto.value)) {
        e.preventDefault(); e.stopImmediatePropagation();
        window.SGR.Alerta.fire({ icon: "error", title: "Código incompleto", text: "Ingrese los 6 dígitos del código recibido por correo." });
        var vacia = casillas.find(function (x) { return !x.value; }); if (vacia) vacia.focus();
      }
    }, true);
  }

  // --- Temporizadores --------------------------------------------------------
  var vence = document.getElementById("vence");
  var reenvio = document.getElementById("estado-reenvio");
  var boton = document.getElementById("btn-reenviar");
  if (vence) {
    var expira = new Date(vence.dataset.expira).getTime();
    var espera = parseInt(reenvio.dataset.espera, 10) || 0;
    var restantes = parseInt(reenvio.dataset.restantes, 10) || 0;
    var finEspera = Date.now() + espera * 1000;
    var avisado = false;
    var tic = function () {
      var s = Math.max(0, Math.round((expira - Date.now()) / 1000));
      vence.textContent = s > 0 ? String(Math.floor(s / 60)).padStart(2, "0") + ":" + String(s % 60).padStart(2, "0") : "vencido";
      if (s === 0 && !avisado) {
        avisado = true;
        window.SGR.Alerta.fire({ icon: "warning", title: "Código vencido", text: "El código venció. Solicite el reenvío para recibir uno nuevo." });
      }
      var e = Math.max(0, Math.ceil((finEspera - Date.now()) / 1000));
      if (restantes <= 0) { reenvio.textContent = "Sin reenvíos disponibles"; boton.disabled = true; }
      else if (e > 0) { reenvio.textContent = "Reenvío disponible en " + e + " s"; boton.disabled = true; }
      else { reenvio.textContent = "Reenvío disponible (" + restantes + " restante" + (restantes === 1 ? "" : "s") + ")"; boton.disabled = false; }
    };
    tic(); setInterval(tic, 1000);
  }

  // --- Requisitos de la nueva contraseña ------------------------------------
  var c1 = document.getElementById("id_clave1");
  var c2 = document.getElementById("id_clave2");
  var lista = document.getElementById("requisitos");
  if (c1 && c2 && lista) {
    var reglas = {
      largo: function (v) { return v.length >= 8 && v.length <= 64; },
      mayuscula: function (v) { return /[A-ZÁÉÍÓÚÑ]/.test(v); },
      minuscula: function (v) { return /[a-záéíóúñ]/.test(v); },
      numero: function (v) { return /\d/.test(v); },
      especial: function (v) { return /[^\w\s]|_/.test(v); },
      coincide: function (v) { return v.length > 0 && v === c2.value; }
    };
    var evaluar = function () {
      var todo = true;
      lista.querySelectorAll("[data-requisito]").forEach(function (li) {
        var ok = reglas[li.dataset.requisito](c1.value);
        todo = todo && ok;
        li.className = ok ? "ok" : "no";
        li.querySelector(".estado-req").textContent = ok ? "(cumplido)" : "(pendiente)";
      });
      c2.setCustomValidity(c2.value && c2.value !== c1.value ? "Las contraseñas no coinciden." : "");
      c1.setCustomValidity(c1.value && !todo && reglas.largo(c1.value) === false ? "La contraseña debe tener entre 8 y 64 caracteres." : "");
      return todo;
    };
    c1.addEventListener("input", evaluar); c2.addEventListener("input", evaluar); evaluar();
    document.getElementById("form-clave").addEventListener("submit", function (e) {
      if (!evaluar()) {
        e.preventDefault(); e.stopImmediatePropagation();
        window.SGR.Alerta.fire({ icon: "error", title: "Contraseña no válida", text: "La contraseña debe cumplir todos los requisitos indicados y coincidir con la confirmación." });
      }
    }, true);
  }
})();
