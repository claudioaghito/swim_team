(function () {
    "use strict";

    var PAGE_SIZES_MM = { A4: { w: 210, h: 297 }, A3: { w: 297, h: 420 } };
    var MARGIN_MM = 10;
    var MM_TO_PX = 96 / 25.4;
    // I browser propongono il "titolo" del documento come nome del file quando si
    // salva la stampa in PDF: lo teniamo da parte per poterlo ripristinare dopo.
    var TITOLO_ORIGINALE = document.title;

    function nomeFileValido(testo) {
        if (!testo) return "";
        return testo
            .replace(/[\r\n]+/g, " ")
            .replace(/[\\/:*?"<>|]/g, "-")
            .replace(/\s+/g, " ")
            .trim()
            .slice(0, 120);
    }

    function impostaTitoloPerStampa() {
        var nome = nomeFileValido(window.STAMPA_NOME_FILE);
        if (nome) document.title = nome;
    }

    function ripristinaTitolo() {
        document.title = TITOLO_ORIGINALE;
    }

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

    function ripristinaStampa() {
        document.body.classList.remove("print-mode");
        var inner = document.getElementById("print-fit-inner");
        if (inner) inner.style.width = "";
        ripristinaTitolo();
    }

    function stampaNormale(formato) {
        document.body.classList.add("print-mode");
        impostaTitoloPerStampa();
        impostaFormatoPagina(formato);
        // Se window.print() viene chiamato nello stesso ciclo in cui abbiamo appena
        // cambiato classi/stili, il browser potrebbe non aver ancora dipinto un frame con
        // il nuovo layout. Il doppio requestAnimationFrame garantisce che almeno un
        // ciclo di paint sia avvenuto prima di aprire il foglio di stampa.
        requestAnimationFrame(function () {
            requestAnimationFrame(function () {
                window.print();
            });
        });
    }

    // "Adatta a 1 pagina": generiamo noi stessi un PDF di una sola pagina via
    // html2canvas + jsPDF, invece di chiedere al dialogo di stampa nativo del
    // dispositivo di scalare il contenuto. Erano gia' stati provati, senza successo
    // affidabile su iOS/Safari (ne' su browser di terze parti come Firefox, che su iOS
    // sono comunque obbligati a usare lo stesso motore WebKit): CSS "zoom" (ignorato
    // dal motore di stampa nativo), "transform: scale()" con area ritagliata (lascia
    // un'area di overflow non scalata che viene comunque conteggiata nell'impaginazione,
    // generando una pagina vuota in piu') e la riduzione proporzionale "vera" di
    // font/padding via custom property CSS (il risultato osservato in stampa restava
    // comunque su 2 pagine, segno che il motore di stampa nativo del dispositivo non è
    // affidabile per questo scopo). Costruendo il PDF noi stessi, la "pagina singola"
    // e' garantita per costruzione: scaliamo l'immagine catturata finche' non entra
    // nell'area utile del foglio, senza passare da nessun motore di impaginazione
    // esterno su cui non abbiamo controllo.
    function esportaPdf(formato) {
        var inner = document.getElementById("print-fit-inner");
        if (!inner) return;
        if (!window.html2canvas || !window.jspdf || !window.jspdf.jsPDF) {
            alert("Impossibile generare il PDF: librerie non disponibili (verifica la connessione a Internet e riprova).");
            return;
        }

        var btn = document.getElementById("print-menu-btn");
        if (btn) btn.disabled = true;

        document.body.classList.add("print-mode");
        // Con il tema scuro attivo (manuale o da preferenza di sistema) gli sfondi di
        // .card/.fase-body/ecc. sono scuri: in stampa reale "@media print" li forza
        // sempre a chiaro (vedi piu' sotto nel foglio di stile), ma qui non stiamo
        // davvero stampando, quindi quella regola non si applica da sola. Il tema
        // chiaro e' quello attivato anche da "data-theme=light" (vedi CSS), che
        // sovrascrive sia la scelta manuale che quella di sistema: lo forziamo solo
        // per la cattura e lo ripristiniamo subito dopo.
        var root = document.documentElement;
        var temaOriginale = root.getAttribute("data-theme");
        root.setAttribute("data-theme", "light");
        // Il tema chiaro usa comunque uno sfondo pagina leggermente grigio (--bg), non
        // bianco puro: lo sovrascriviamo qui, cosi' anche gli spazi tra le card nel PDF
        // risultano bianchi (stesso sfondo bianco forzato dalla stampa reale, vedi
        // "@media print" piu' sotto nel foglio di stile, che pero' da sola non si
        // applica a una cattura che non e' una stampa vera).
        var bgOriginale = document.body.style.backgroundColor;
        document.body.style.backgroundColor = "#ffffff";
        var size = PAGE_SIZES_MM[formato] || PAGE_SIZES_MM.A4;
        var pageWpx = (size.w - MARGIN_MM * 2) * MM_TO_PX;
        // Stessa larghezza che avrebbe il contenuto stampato sul foglio scelto (non la
        // larghezza dello schermo, altrimenti su un telefono la resa sarebbe sbagliata).
        inner.style.width = pageWpx + "px";

        function pulisci() {
            if (btn) btn.disabled = false;
            document.body.classList.remove("print-mode");
            inner.style.width = "";
            if (temaOriginale === null) root.removeAttribute("data-theme");
            else root.setAttribute("data-theme", temaOriginale);
            document.body.style.backgroundColor = bgOriginale;
        }

        // Doppio requestAnimationFrame: come per la stampa normale, assicura che il
        // nuovo layout (print-mode, larghezza pagina) sia stato dipinto almeno una
        // volta prima che html2canvas lo catturi.
        requestAnimationFrame(function () {
            requestAnimationFrame(function () {
                html2canvas(inner, {
                    scale: Math.min(window.devicePixelRatio || 1, 2),
                    backgroundColor: "#ffffff",
                    useCORS: true
                }).then(function (canvas) {
                    var contentWmm = size.w - MARGIN_MM * 2;
                    var contentHmm = size.h - MARGIN_MM * 2;
                    var imgWmm = contentWmm;
                    var imgHmm = imgWmm * (canvas.height / canvas.width);
                    if (imgHmm > contentHmm) {
                        var fattore = contentHmm / imgHmm;
                        imgHmm = contentHmm;
                        imgWmm = imgWmm * fattore;
                    }
                    var x = MARGIN_MM + (contentWmm - imgWmm) / 2;

                    var jsPDF = window.jspdf.jsPDF;
                    var doc = new jsPDF({ orientation: "portrait", unit: "mm", format: [size.w, size.h] });
                    doc.addImage(canvas.toDataURL("image/jpeg", 0.92), "JPEG", x, MARGIN_MM, imgWmm, imgHmm);
                    var nome = nomeFileValido(window.STAMPA_NOME_FILE) || "allenamento";
                    doc.save(nome + ".pdf");
                }).catch(function () {
                    alert("Non e' stato possibile generare il PDF. Riprova.");
                }).then(pulisci, pulisci);
            });
        });
    }

    function stampaAllenamento(formato, adatta) {
        chiudiMenu();
        if (adatta) {
            esportaPdf(formato);
        } else {
            stampaNormale(formato);
        }
    }

    window.stampaAllenamento = stampaAllenamento;

    // L'evento "afterprint" non e' affidabile su tutti i dispositivi (es. il dialogo di
    // stampa nativo di Android non lo scatena sempre): ripristiniamo il layout normale
    // con piu' meccanismi di sicurezza, cosi' non restano stili residui che rompono il
    // resto della pagina. Riguardano solo "stampa normale" (window.print()): "adatta a
    // 1 pagina" si ripulisce da se' alla fine di esportaPdf().
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
