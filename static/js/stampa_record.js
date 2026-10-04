(function () {
    "use strict";

    // I record societari sono troppi per stare su una pagina sola (5 stili x 14
    // categorie): la stampa nativa del browser li spezzava a meta' tabella,
    // lasciando una pagina quasi vuota con la sola ultima riga (es. M90) ogni
    // volta che una sezione non entrava per intero nello spazio residuo di
    // pagina, oltre a una prima pagina quasi vuota con il solo titolo. Per lo
    // stesso motivo gia' incontrato con gli allenamenti (vedi stampa_allenamento.js),
    // il motore di impaginazione nativo non e' affidabile per garantire che ogni
    // sezione stia su una pagina: generiamo quindi noi stessi un PDF via
    // html2canvas + jsPDF, con una pagina A4 orizzontale per ogni sezione
    // (.record-card), scalando l'immagine catturata solo se necessario per
    // entrare nell'area utile del foglio. Cosi' ogni sezione occupa sempre e
    // soltanto le pagine che le servono, senza mai lasciarne una quasi vuota.

    var PAGE_MM = { w: 297, h: 210 };
    var MARGIN_MM = 10;
    var MM_TO_PX = 96 / 25.4;

    function nomeFileValido(testo) {
        if (!testo) return "";
        return testo
            .replace(/[\r\n]+/g, " ")
            .replace(/[\\/:*?"<>|]/g, "-")
            .replace(/\s+/g, " ")
            .trim()
            .slice(0, 120);
    }

    function esportaRecordPdf() {
        var cards = document.querySelectorAll(".record-card");
        if (!cards.length) return;
        if (!window.html2canvas || !window.jspdf || !window.jspdf.jsPDF) {
            alert("Impossibile generare il PDF: librerie non disponibili (verifica la connessione a Internet e riprova).");
            return;
        }

        var btn = document.getElementById("stampa-record-btn");
        if (btn) btn.disabled = true;

        document.body.classList.add("print-mode");
        // Stesso motivo di stampa_allenamento.js: forziamo tema chiaro e sfondo
        // bianco puro durante la cattura, poi li ripristiniamo.
        var root = document.documentElement;
        var temaOriginale = root.getAttribute("data-theme");
        root.setAttribute("data-theme", "light");
        var bgOriginale = document.body.style.backgroundColor;
        document.body.style.backgroundColor = "#ffffff";

        var contentWmm = PAGE_MM.w - MARGIN_MM * 2;
        var contentHmm = PAGE_MM.h - MARGIN_MM * 2;
        var pageWpx = contentWmm * MM_TO_PX;

        // .card ha "max-width:100%" e "overflow-x:auto" (per lo scroll orizzontale a
        // schermo): li neutralizziamo qui, altrimenti su schermi stretti (es. telefono)
        // la larghezza forzata sotto verrebbe comunque limitata alla larghezza del
        // viewport invece che a quella reale della pagina PDF.
        var stiliOriginali = [];
        cards.forEach(function (card) {
            stiliOriginali.push({
                width: card.style.width,
                maxWidth: card.style.maxWidth,
                overflow: card.style.overflow
            });
            card.style.width = pageWpx + "px";
            card.style.maxWidth = "none";
            card.style.overflow = "visible";
        });

        function pulisci() {
            if (btn) btn.disabled = false;
            document.body.classList.remove("print-mode");
            cards.forEach(function (card, i) {
                card.style.width = stiliOriginali[i].width;
                card.style.maxWidth = stiliOriginali[i].maxWidth;
                card.style.overflow = stiliOriginali[i].overflow;
            });
            if (temaOriginale === null) root.removeAttribute("data-theme");
            else root.setAttribute("data-theme", temaOriginale);
            document.body.style.backgroundColor = bgOriginale;
        }

        requestAnimationFrame(function () {
            requestAnimationFrame(function () {
                var jsPDF = window.jspdf.jsPDF;
                var doc = null;

                var catture = Array.prototype.reduce.call(cards, function (promessa, card) {
                    return promessa.then(function () {
                        return html2canvas(card, {
                            scale: Math.min(window.devicePixelRatio || 1, 2),
                            backgroundColor: "#ffffff",
                            useCORS: true
                        });
                    }).then(function (canvas) {
                        var imgWmm = contentWmm;
                        var imgHmm = imgWmm * (canvas.height / canvas.width);
                        if (imgHmm > contentHmm) {
                            imgWmm = imgWmm * (contentHmm / imgHmm);
                            imgHmm = contentHmm;
                        }
                        var x = MARGIN_MM + (contentWmm - imgWmm) / 2;
                        if (!doc) {
                            doc = new jsPDF({ orientation: "landscape", unit: "mm", format: "a4" });
                        } else {
                            doc.addPage("a4", "landscape");
                        }
                        doc.addImage(canvas.toDataURL("image/jpeg", 0.92), "JPEG", x, MARGIN_MM, imgWmm, imgHmm);
                    });
                }, Promise.resolve());

                catture.then(function () {
                    var nome = nomeFileValido(window.STAMPA_NOME_FILE) || "record-societari";
                    doc.save(nome + ".pdf");
                }).catch(function () {
                    alert("Non e' stato possibile generare il PDF. Riprova.");
                }).then(pulisci, pulisci);
            });
        });
    }

    window.esportaRecordPdf = esportaRecordPdf;
})();
