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

    // Collega l'ombra/hint di scorrimento a un elemento .fase-table-scroll, anche se
    // e' stato aggiunto al DOM dopo il caricamento iniziale (es. dal builder del piano).
    function inizializzaElemento(el) {
        if (el.dataset.ftsInit) return;
        el.dataset.ftsInit = "1";
        el.addEventListener("scroll", function () { aggiornaOmbre(el); }, { passive: true });
    }

    function aggiornaTutto() {
        document.querySelectorAll(".fase-table-scroll").forEach(function (el) {
            inizializzaElemento(el);
            aggiornaOmbre(el);
            aggiornaHint(el);
        });
    }

    document.addEventListener("DOMContentLoaded", aggiornaTutto);

    var timer = null;
    window.addEventListener("resize", function () {
        clearTimeout(timer);
        timer = setTimeout(aggiornaTutto, 150);
    });
    window.addEventListener("afterprint", aggiornaTutto);

    // Esposto cosi' il builder del piano (piano_allenamento.js) puo' ricalcolare
    // ombre/hint quando aggiunge tabelle dopo il caricamento della pagina.
    window.FaseTableScroll = { aggiorna: aggiornaTutto };
})();
