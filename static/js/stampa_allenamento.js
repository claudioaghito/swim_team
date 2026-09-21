(function () {
    "use strict";

    var PAGE_SIZES_MM = { A4: { w: 210, h: 297 }, A3: { w: 297, h: 420 } };
    var MARGIN_MM = 10;
    var MM_TO_PX = 96 / 25.4;

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
        var outer = document.getElementById("print-fit-outer");
        if (inner) { inner.style.transform = ""; inner.style.width = ""; }
        if (outer) { outer.style.height = ""; outer.style.overflow = ""; }
    }

    function adattaAUnaPagina(formato) {
        var inner = document.getElementById("print-fit-inner");
        var outer = document.getElementById("print-fit-outer");
        if (!inner || !outer) return;

        ripristinaAdattamento();

        var size = PAGE_SIZES_MM[formato] || PAGE_SIZES_MM.A4;
        var pageWpx = (size.w - MARGIN_MM * 2) * MM_TO_PX;
        var pageHpx = (size.h - MARGIN_MM * 2) * MM_TO_PX;

        var rect = inner.getBoundingClientRect();
        var naturalW = rect.width;
        var naturalH = rect.height;
        if (!naturalW || !naturalH) return;

        var scale = Math.min(pageWpx / naturalW, pageHpx / naturalH, 1);

        inner.style.width = naturalW + "px";
        inner.style.transformOrigin = "top left";
        inner.style.transform = "scale(" + scale + ")";
        outer.style.height = (naturalH * scale) + "px";
        outer.style.overflow = "hidden";
    }

    function stampaAllenamento(formato, adatta) {
        chiudiMenu();
        impostaFormatoPagina(formato);
        if (adatta) {
            adattaAUnaPagina(formato);
        } else {
            ripristinaAdattamento();
        }
        setTimeout(function () { window.print(); }, 30);
    }

    window.addEventListener("afterprint", ripristinaAdattamento);
    window.stampaAllenamento = stampaAllenamento;

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
