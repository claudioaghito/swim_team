(function () {
    "use strict";

    var PAGE_SIZES_MM = { A4: { w: 210, h: 297 }, A3: { w: 297, h: 420 } };
    var MARGIN_MM = 10;
    var MM_TO_PX = 96 / 25.4;
    // "zoom" (non standard ma supportato da Chrome/Edge/WebView Android) ridimensiona
    // anche il layout, non solo l'aspetto visivo: a differenza di transform: scale(),
    // l'impaginazione di stampa lo rispetta e non lascia pagine vuote residue.
    var SUPPORTA_ZOOM = "zoom" in document.documentElement.style;

    function chiudiMenu() {
        var menu = document.getElementById("print-menu");
        var btn = document.getElementById("print-menu-btn");
        if (menu) menu.hidden = true;
        if (btn) btn.setAttribute("aria-expanded", "false");
    }

    function toggleMenu() {
        var menu = document.getElementById("print-menu");
        var btn = document.getElementById("print-menu-btn");
        if (!menu || !btn) return;
        var apri = menu.hidden;
        if (apri) ripristinaStampa();
        menu.hidden = !apri;
        btn.setAttribute("aria-expanded", apri ? "true" : "false");
    }

    function impostaFormatoPagina(formato) {
        var style = document.getElementById("print-page-style");
        if (!style) {
            style = document.createElement("style");
            style.id = "print-page-style";
            document.head.appendChild(style);
        }
        var size = PAGE_SIZES_MM[formato] || PAGE_SIZES_MM.A4;
        style.textContent = "@page { size: " + size.w + "mm " + size.h + "mm; margin: " + MARGIN_MM + "mm; }";
    }

    function ripristinaAdattamento() {
        var inner = document.getElementById("print-fit-inner");
        if (!inner) return;
        inner.style.width = "";
        inner.style.zoom = "";
        inner.style.transform = "";
        inner.style.transformOrigin = "";
    }

    function adattaAUnaPagina(formato) {
        var inner = document.getElementById("print-fit-inner");
        if (!inner) return;

        ripristinaAdattamento();

        var size = PAGE_SIZES_MM[formato] || PAGE_SIZES_MM.A4;
        var pageWpx = (size.w - MARGIN_MM * 2) * MM_TO_PX;
        var pageHpx = (size.h - MARGIN_MM * 2) * MM_TO_PX;

        // Misura l'altezza reale del contenuto alla larghezza piena del foglio scelto
        // (non alla larghezza dello schermo, altrimenti su un telefono il calcolo e' sbagliato).
        inner.style.width = pageWpx + "px";
        var naturalH = inner.scrollHeight;
        if (!naturalH) return;

        var scale = Math.min(pageHpx / naturalH, 1);
        if (scale >= 1) return; // ci sta gia' su una pagina: nessun rimpicciolimento necessario

        if (SUPPORTA_ZOOM) {
            inner.style.zoom = scale;
            // compensa: a larghezza pageWpx/scale, con zoom scale, la larghezza finale torna pageWpx
            inner.style.width = (pageWpx / scale) + "px";
        } else {
            inner.style.transformOrigin = "top left";
            inner.style.transform = "scale(" + scale + ")";
            inner.style.width = (pageWpx / scale) + "px";
        }
    }

    function ripristinaStampa() {
        document.body.classList.remove("print-mode");
        ripristinaAdattamento();
    }

    function stampaAllenamento(formato, adatta) {
        chiudiMenu();
        // In stampa le tabelle tornano al layout "a capo su larghezza fissa" (vedi CSS
        // .print-mode): va applicato PRIMA di misurare l'altezza per "adatta a 1 pagina",
        // altrimenti la misura non corrisponderebbe a quello che verra' davvero stampato.
        document.body.classList.add("print-mode");
        impostaFormatoPagina(formato);
        if (adatta) {
            adattaAUnaPagina(formato);
        } else {
            ripristinaAdattamento();
        }
        window.print();
    }

    window.stampaAllenamento = stampaAllenamento;

    // L'evento "afterprint" non e' affidabile su tutti i dispositivi (es. il dialogo di
    // stampa nativo di Android non lo scatena sempre): ripristiniamo il layout normale
    // con piu' meccanismi di sicurezza, cosi' non restano stili residui che rompono il
    // resto della pagina.
    window.addEventListener("afterprint", ripristinaStampa);
    if (window.matchMedia) {
        try {
            window.matchMedia("print").addEventListener("change", function (e) {
                if (!e.matches) ripristinaStampa();
            });
        } catch (e) {}
    }
    document.addEventListener("visibilitychange", function () {
        if (document.visibilityState === "visible") ripristinaStampa();
    });
    window.addEventListener("pageshow", ripristinaStampa);
    window.addEventListener("focus", ripristinaStampa);

    document.addEventListener("DOMContentLoaded", function () {
        var btn = document.getElementById("print-menu-btn");
        var menu = document.getElementById("print-menu");
        if (!btn || !menu) return;

        btn.addEventListener("click", function (e) {
            e.stopPropagation();
            toggleMenu();
        });
        menu.addEventListener("click", function (e) {
            var item = e.target.closest("[data-formato]");
            if (!item) return;
            stampaAllenamento(item.getAttribute("data-formato"), item.getAttribute("data-adatta") === "1");
        });
        document.addEventListener("click", function (e) {
            if (!menu.hidden && !menu.contains(e.target) && e.target !== btn && !btn.contains(e.target)) {
                chiudiMenu();
            }
        });
        document.addEventListener("keydown", function (e) {
            if (e.key === "Escape") chiudiMenu();
        });
    });
})();
