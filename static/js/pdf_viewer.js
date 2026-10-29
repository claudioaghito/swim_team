/* Anteprima PDF ad alta risoluzione (pdf.js), usata da cartellini, certificati,
   programmi gara e allegati dei messaggi.

   Ogni pagina viene disegnata su un canvas con molti piu' pixel di quelli mostrati
   (densita' dello schermo x un fattore extra per lo zoom a due dita) e poi ridotta via CSS
   alla larghezza del contenitore: cosi' ingrandendo il testo resta nitido. */
(function () {
    var PDFJS_WORKER = "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js";
    var ZOOM_EXTRA = 1.5;          // margine di risoluzione per lo zoom
    var MAX_LARGHEZZA_PX = 3200;   // limiti per non esaurire la memoria dei telefoni
    var MAX_PIXEL_TOTALI = 9000000;

    function mostraErrore(container, downloadUrl) {
        container.innerHTML = "<p>Impossibile visualizzare l'anteprima del PDF in questa pagina. " +
            "<a href=\"" + downloadUrl + "\">Scaricalo</a> per aprirlo.</p>";
    }

    function renderPagina(pdf, numeroPagina, container) {
        return pdf.getPage(numeroPagina).then(function (pagina) {
            var base = pagina.getViewport({ scale: 1 });
            var larghezzaCss = container.clientWidth || base.width;
            var scalaCss = larghezzaCss / base.width;

            var densita = Math.max(window.devicePixelRatio || 1, 2) * ZOOM_EXTRA;
            var scalaRender = scalaCss * densita;
            // riduce la risoluzione solo se supera i limiti di larghezza o di memoria
            scalaRender = Math.min(
                scalaRender,
                MAX_LARGHEZZA_PX / base.width,
                Math.sqrt(MAX_PIXEL_TOTALI / (base.width * base.height))
            );
            scalaRender = Math.max(scalaRender, scalaCss);

            var viewport = pagina.getViewport({ scale: scalaRender });
            var canvas = document.createElement("canvas");
            canvas.width = Math.floor(viewport.width);
            canvas.height = Math.floor(viewport.height);
            canvas.style.display = "block";
            canvas.style.width = "100%";
            canvas.style.height = "auto";
            canvas.style.marginBottom = "12px";
            container.appendChild(canvas);

            return pagina.render({ canvasContext: canvas.getContext("2d"), viewport: viewport }).promise;
        });
    }

    window.mostraPdf = function (container, url, downloadUrl) {
        if (!window.pdfjsLib) {
            mostraErrore(container, downloadUrl);
            return;
        }
        pdfjsLib.GlobalWorkerOptions.workerSrc = PDFJS_WORKER;
        pdfjsLib.getDocument(url).promise.then(function (pdf) {
            container.innerHTML = "";
            var catena = Promise.resolve();
            for (var i = 1; i <= pdf.numPages; i++) {
                (function (numeroPagina) {
                    catena = catena.then(function () { return renderPagina(pdf, numeroPagina, container); });
                })(i);
            }
            return catena;
        }).catch(function () { mostraErrore(container, downloadUrl); });
    };
})();
