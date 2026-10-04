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

    function creaDialogAnteprima() {
        var dialog = document.getElementById("pdf-preview-dialog");
        if (dialog) return dialog;
        dialog = document.createElement("dialog");
        dialog.id = "pdf-preview-dialog";
        dialog.className = "pdf-preview-dialog";
        dialog.innerHTML =
            '<div class="pdf-preview-header">' +
                '<span>Anteprima PDF</span>' +
                '<button type="button" id="pdf-preview-close" aria-label="Chiudi" title="Chiudi">×</button>' +
            '</div>' +
            '<div id="pdf-preview-pages" class="pdf-preview-pages"></div>' +
            '<div class="pdf-preview-actions">' +
                '<button type="button" id="pdf-preview-annulla">Annulla</button>' +
                '<button type="button" class="btn" id="pdf-preview-scarica">' + '⬇' + ' Scarica PDF</button>' +
            '</div>';
        document.body.appendChild(dialog);
        return dialog;
    }

    // Apriamo subito il dialogo, con un semplice messaggio di caricamento, PRIMA di
    // forzare tema chiaro/sfondo bianco sulla pagina sottostante per la cattura: senza
    // questo, l'utente vedrebbe per i secondi della cattura la pagina reale "sfarfallare"
    // in chiaro, dietro al punto in cui comparira' poi l'anteprima vera. Il dialogo a
    // schermo intero copre subito la pagina, quindi quel passaggio non si vede piu'.
    function mostraCaricamento() {
        var dialog = creaDialogAnteprima();
        dialog.querySelector("#pdf-preview-pages").innerHTML =
            '<p class="pdf-preview-loading">Generazione del PDF in corso…</p>';
        dialog.querySelector("#pdf-preview-close").hidden = true;
        dialog.querySelector("#pdf-preview-annulla").hidden = true;
        dialog.querySelector("#pdf-preview-scarica").hidden = true;
        if (typeof dialog.showModal === "function" && !dialog.open) dialog.showModal();
        return dialog;
    }

    // Sostituisce il messaggio di caricamento con le pagine vere e proprie (le stesse
    // immagini gia' catturate che finiscono nel PDF: niente <iframe>, su Chrome Android
    // non ha un visualizzatore PDF integrato e mostrerebbe solo una card di download).
    function mostraAnteprima(dialog, doc, nomeFile, immaginiPagine) {
        return new Promise(function (resolve) {
            var pagine = dialog.querySelector("#pdf-preview-pages");
            pagine.innerHTML = "";
            immaginiPagine.forEach(function (dataUrl) {
                var img = document.createElement("img");
                img.className = "pdf-preview-page";
                img.src = dataUrl;
                img.alt = "Pagina PDF";
                pagine.appendChild(img);
            });

            var btnChiudi = dialog.querySelector("#pdf-preview-close");
            var btnAnnulla = dialog.querySelector("#pdf-preview-annulla");
            var btnScarica = dialog.querySelector("#pdf-preview-scarica");
            btnChiudi.hidden = false;
            btnAnnulla.hidden = false;
            btnScarica.hidden = false;

            function cleanup() {
                btnChiudi.removeEventListener("click", chiudi);
                btnAnnulla.removeEventListener("click", chiudi);
                btnScarica.removeEventListener("click", scarica);
                dialog.removeEventListener("cancel", chiudi);
            }
            function chiudi() {
                cleanup();
                dialog.close();
                pagine.innerHTML = "";
                resolve();
            }
            function scarica() {
                doc.save(nomeFile + ".pdf");
                chiudi();
            }

            btnChiudi.addEventListener("click", chiudi);
            btnAnnulla.addEventListener("click", chiudi);
            btnScarica.addEventListener("click", scarica);
            dialog.addEventListener("cancel", chiudi);

            if (typeof dialog.showModal !== "function") {
                // Fallback per browser senza <dialog> nativo: scarichiamo direttamente,
                // non c'e' un modo affidabile per mostrare un'anteprima modale.
                scarica();
            } else if (!dialog.open) {
                dialog.showModal();
            }
        });
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

        var dialog = mostraCaricamento();

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
                var immaginiPagine = [];

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
                        var dataUrl = canvas.toDataURL("image/jpeg", 0.92);
                        immaginiPagine.push(dataUrl);
                        if (!doc) {
                            doc = new jsPDF({ orientation: "landscape", unit: "mm", format: "a4" });
                        } else {
                            doc.addPage("a4", "landscape");
                        }
                        doc.addImage(dataUrl, "JPEG", x, MARGIN_MM, imgWmm, imgHmm);
                    });
                }, Promise.resolve());

                catture.then(function () {
                    // Il PDF e' gia' pronto in memoria: ripristiniamo subito tema/layout
                    // della pagina (l'anteprima mostra le immagini gia' catturate, non ha
                    // piu' bisogno dello stato "da stampa" sulla pagina sottostante).
                    pulisci();
                    var nome = nomeFileValido(window.STAMPA_NOME_FILE) || "record-societari";
                    return mostraAnteprima(dialog, doc, nome, immaginiPagine);
                }).catch(function () {
                    pulisci();
                    dialog.close();
                    alert("Non e' stato possibile generare il PDF. Riprova.");
                });
            });
        });
    }

    window.esportaRecordPdf = esportaRecordPdf;
})();
