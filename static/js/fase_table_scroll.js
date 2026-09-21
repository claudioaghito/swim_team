(function () {
    "use strict";

    var TOLLERANZA = 2;

    function aggiornaOmbre(el) {
        var scrollaSinistra = el.scrollLeft > TOLLERANZA;
        var scrollaDestra = el.scrollLeft < (el.scrollWidth - el.clientWidth - TOLLERANZA);
        el.classList.toggle("scroll-left", scrollaSinistra);
        el.classList.toggle("scroll-right", scrollaDestra);
    }

    function aggiornaHint(el) {
        var hint = el.previousElementSibling;
        if (!hint || !hint.classList.contains("fase-table-hint")) return;
        hint.hidden = el.scrollWidth <= el.clientWidth + TOLLERANZA;
    }

    function aggiornaTutto() {
        document.querySelectorAll(".fase-table-scroll").forEach(function (el) {
            aggiornaOmbre(el);
            aggiornaHint(el);
        });
    }

    document.addEventListener("DOMContentLoaded", function () {
        document.querySelectorAll(".fase-table-scroll").forEach(function (el) {
            aggiornaOmbre(el);
            aggiornaHint(el);
            el.addEventListener("scroll", function () { aggiornaOmbre(el); }, { passive: true });
        });
    });

    var timer = null;
    window.addEventListener("resize", function () {
        clearTimeout(timer);
        timer = setTimeout(aggiornaTutto, 150);
    });
    window.addEventListener("afterprint", aggiornaTutto);
})();
