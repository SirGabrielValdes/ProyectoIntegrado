/* Tubo de trabajo: arrastrar tarjetas a la etapa siguiente (SortableJS, mouse y pantalla táctil). */
(function () {
  "use strict";
  var tablero = document.querySelector("[data-tablero-arrastrable]");
  if (!tablero || !window.Sortable) return;
  var form = document.getElementById("form-arrastre");
  var Alerta = window.SGR && window.SGR.Alerta;

  // Última posición conocida del puntero (respaldo si el evento de soltar no trae coordenadas).
  var puntero = { x: 0, y: 0 };
  ["pointermove", "mousemove"].forEach(function (tipo) {
    document.addEventListener(tipo, function (e) { puntero.x = e.clientX; puntero.y = e.clientY; }, { passive: true });
  });
  document.addEventListener("touchmove", function (e) {
    if (e.touches && e.touches[0]) { puntero.x = e.touches[0].clientX; puntero.y = e.touches[0].clientY; }
  }, { passive: true });

  // Punto exacto donde se soltó la tarjeta (mouse, lápiz o dedo).
  function puntoFinal(evt) {
    var e = evt.originalEvent;
    if (e && e.changedTouches && e.changedTouches[0]) return { x: e.changedTouches[0].clientX, y: e.changedTouches[0].clientY };
    if (e && typeof e.clientX === "number" && (e.clientX || e.clientY)) return { x: e.clientX, y: e.clientY };
    return { x: puntero.x, y: puntero.y };
  }

  // Columna del tablero bajo ese punto (cualquier parte: cabecera, tarjetas o espacio libre),
  // ignorando la copia flotante de la tarjeta que sigue al puntero.
  function columnaEn(punto) {
    var capas = document.elementsFromPoint ? document.elementsFromPoint(punto.x, punto.y)
                                           : [document.elementFromPoint(punto.x, punto.y)];
    for (var i = 0; i < capas.length; i++) {
      var el = capas[i];
      if (!el || el.closest(".sortable-fallback")) continue;
      var col = el.closest(".kanban__columna");
      if (col && tablero.contains(col)) return col;
    }
    return null;
  }

  function nombreEtapa(estado) {
    var l = tablero.querySelector('.kanban__lista[data-estado="' + estado + '"]');
    return l ? l.dataset.nombre : estado;
  }

  function devolver(evt) {
    // Deja la tarjeta exactamente donde estaba.
    var origen = evt.from, item = evt.item;
    origen.insertBefore(item, origen.children[evt.oldIndex] || null);
  }

  function aviso(icono, titulo, texto, html) {
    if (Alerta) return Alerta.fire({ icon: icono, title: titulo, text: texto, html: html });
    window.alert(titulo + "\n" + texto);
    return Promise.resolve({ isConfirmed: false });
  }

  tablero.querySelectorAll(".kanban__lista").forEach(function (lista) {
    Sortable.create(lista, {
      group: {
        name: "tubo",
        pull: true,
        // Solo se acepta la tarjeta en la columna de su etapa siguiente.
        put: function (destino, origen, tarjeta) {
          return destino.el.dataset.estado === tarjeta.dataset.siguiente;
        }
      },
      sort: false,
      draggable: ".tarjeta-tubo",
      filter: '.kanban__vacio, a, button, input, form, .tarjeta-tubo[data-siguiente=""]',
      preventOnFilter: false,
      forceFallback: true,
      fallbackTolerance: 5,
      animation: 150,
      ghostClass: "tarjeta-tubo--fantasma",
      chosenClass: "tarjeta-tubo--elegida",
      onMove: function (evt) {
        return evt.to.dataset.estado === evt.dragged.dataset.siguiente;
      },
      onStart: function (evt) {
        var siguiente = evt.item.dataset.siguiente;
        tablero.querySelectorAll(".kanban__lista").forEach(function (l) {
          l.classList.toggle("kanban__lista--destino", l.dataset.estado === siguiente);
        });
      },
      onEnd: function (evt) {
        tablero.querySelectorAll(".kanban__lista--destino").forEach(function (l) {
          l.classList.remove("kanban__lista--destino");
        });
        var tarjeta = evt.item, siguiente = tarjeta.dataset.siguiente;
        // La decisión depende SOLO de la columna sobre la que se soltó, no de dónde alcanzó
        // a insertar la tarjeta la librería durante el arrastre.
        var columna = columnaEn(puntoFinal(evt));
        var destino = columna && columna.querySelector(".kanban__lista");
        if (destino === evt.from) {            // se soltó en su misma columna: sin cambios
          if (evt.from !== evt.to) devolver(evt);
          return;
        }
        if (!destino || destino.dataset.estado !== siguiente) {
          devolver(evt);
          if (siguiente) {
            aviso("info", "Movimiento no permitido",
                  tarjeta.dataset.codigo + " solo puede avanzar a la etapa siguiente: «" +
                  nombreEtapa(siguiente) + "». Suelte la tarjeta sobre esa columna.");
          }
          return;
        }
        if (tarjeta.parentNode !== destino) {  // se soltó en la columna correcta: la tarjeta queda ahí
          var vacio = destino.querySelector(".kanban__vacio");
          destino.insertBefore(tarjeta, vacio || destino.firstChild);
        }
        if (destino.dataset.estado === "REALIZADO" && tarjeta.dataset.evidenciaAprobada !== "1") {
          devolver(evt);
          aviso("error", "Falta evidencia aprobada", null,
                "Para pasar <strong>" + tarjeta.dataset.codigo + "</strong> a «Realizados» se necesita al menos una " +
                "foto de evidencia aprobada por el delegado.<br><a href=\"" + tarjeta.dataset.urlDetalle +
                "#evidencias\">Ir a las evidencias del compromiso</a>");
          return;
        }
        var nombre = destino.dataset.nombre;
        var confirmar = Alerta ? Alerta.fire({
          icon: "question", title: "Mover compromiso",
          text: "¿Mover " + tarjeta.dataset.codigo + " a «" + nombre + "»? Quedará registrado en su historial.",
          showCancelButton: true, confirmButtonText: "Mover"
        }) : Promise.resolve({ isConfirmed: window.confirm("¿Mover " + tarjeta.dataset.codigo + " a " + nombre + "?") });
        confirmar.then(function (r) {
          if (!r.isConfirmed) {
            devolver(evt);
            if (Alerta) Alerta.fire({ icon: "info", title: "Operación cancelada", text: "La tarjeta no se movió.", timer: 2000 });
            return;
          }
          form.action = tarjeta.dataset.urlAvanzar;
          form.querySelector("[name=destino]").value = destino.dataset.estado;
          if (Alerta) Alerta.fire({ title: "Moviendo…", allowOutsideClick: false, didOpen: function () { Swal.showLoading(); } });
          form.submit();
        });
      }
    });
  });
})();
