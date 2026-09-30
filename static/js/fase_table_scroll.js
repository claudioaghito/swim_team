(function () {
    "use strict";

    var TOLLERANZA = 2;

    function aggiornaHint(el) {
        var hint = el.previousElementSibling;
        if (!hint || !hint.classList.contains("fase-table-hint")) return;
        hint.hidden = el.scrollWidth <= el.clientWidth + TOLLERANZA;
    }

    function aggiornaTutto() {
        // Niente piu' ombra/classe scroll-left/scroll-right legata all'evento "scroll":
        // su alcuni browser/WebView Android l'ombra a gradiente, animata a ogni scroll
        // della tabella, restava incollata sullo schermo come una fascia semitrasparente
        // anche fuori dai bordi della tabella. Resta solo il testo di aiuto sopra la
        // tabella, che non ha questo problema perche' non cambia durante lo scroll.
        document.querySelectorAll(".fase-table-scroll").forEach(aggiornaHint);
    }

    document.addEventListener("DOMContentLoaded", aggiornaTutto);

    var timer = null;
    window.addEventListener("resize", function () {
        clearTimeout(timer);
        timer = setTimeout(aggiornaTutto, 150);
    });
    window.addEventListener("afterprint", aggiornaTutto);

    // Esposto cosi' il builder del piano (piano_allenamento.js) puo' ricalcolare
    // l'hint quando aggiunge tabelle dopo il caricamento della pagina.
    window.FaseTableScroll = { aggiorna: aggiornaTutto };
})();
