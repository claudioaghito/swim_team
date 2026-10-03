(function () {
    "use strict";

    var PAGE_SIZES_MM = { A4: { w: 210, h: 297 }, A3: { w: 297, h: 420 } };
    var MARGIN_MM = 10;
    // Le anteprime di stampa NATIVE di iOS e Android (non quella del browser desktop)
    // aggiungono in automatico un'intestazione/piede pagina (titolo, data, "Pagina X di
    // Y") che occupa spazio reale sul foglio ma non fa parte del margine CSS "@page":
    // il nostro calcolo non puo' saperne l'altezza esatta (varia per OS/stampante), quindi
    // in fase di "adatta a 1 pagina" consideriamo l'area utile piu' piccola di questo
    // margine extra, cosi' il contenuto scalato ci sta comunque anche con quello spazio
    // in meno. Si applica solo al calcolo della scala, non al margine "@page" vero e
    // proprio (che resta identico anche per la stampa "normale").
    var MARGINE_SICUREZZA_ADATTA_MM = 20;
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

    function ripristinaAdattamento() {
        var inner = document.getElementById("print-fit-inner");
        if (inner) {
            inner.style.width = "";
            inner.style.fontSize = "";
        }
    }

    function adattaAUnaPagina(formato) {
        var inner = document.getElementById("print-fit-inner");
        if (!inner) return;

        ripristinaAdattamento();

        var size = PAGE_SIZES_MM[formato] || PAGE_SIZES_MM.A4;
        var pageWpx = (size.w - MARGIN_MM * 2) * MM_TO_PX;
        var pageHpx = (size.h - MARGIN_MM * 2 - MARGINE_SICUREZZA_ADATTA_MM) * MM_TO_PX;

        // Misura l'altezza reale del contenuto alla larghezza piena del foglio scelto
        // (non alla larghezza dello schermo, altrimenti su un telefono il calcolo e' sbagliato).
        inner.style.width = pageWpx + "px";
        if (!inner.scrollHeight || inner.scrollHeight <= pageHpx) { inner.style.width = ""; return; } // ci sta gia' su una pagina

        // Qui sotto erano gia' state provate "zoom" e poi "transform: scale()" (con un
        // contenitore esterno ad altezza fissa per simulare il ridimensionamento nel
        // flusso di stampa): la prima non viene rispettata dal motore di stampa nativo
        // di iOS/Safari (scala solo a schermo), la seconda sembra rispettata nella resa
        // visiva ma lascia comunque, dietro le quinte, un'area di contenuto alla sua
        // altezza NON scalata (quella "ritagliata" via overflow/posizionamento): Safari
        // la conta ugualmente nell'impaginazione di stampa e genera una pagina vuota in
        // piu', anche se a schermo non si vede nulla oltre il bordo.
        // Riducendo invece davvero la dimensione del testo (font-size, proprieta' CSS
        // standard rispettata ovunque) l'altezza di LAYOUT del contenuto si riduce per
        // davvero: non resta alcuna area di overflow nascosta da poter conteggiare per
        // errore, quindi niente piu' pagine vuote residue.
        var percento = 100;
        while (inner.scrollHeight > pageHpx && percento > 40) {
            percento -= 3;
            inner.style.fontSize = percento + "%";
        }
    }

    function ripristinaStampa() {
        document.body.classList.remove("print-mode");
        ripristinaAdattamento();
        ripristinaTitolo();
    }

    function stampaAllenamento(formato, adatta) {
        chiudiMenu();
        // In stampa le tabelle tornano al layout "a capo su larghezza fissa" (vedi CSS
        // .print-mode): va applicato PRIMA di misurare l'altezza per "adatta a 1 pagina",
        // altrimenti la misura non corrisponderebbe a quello che verra' davvero stampato.
        document.body.classList.add("print-mode");
        impostaTitoloPerStampa();
        impostaFormatoPagina(formato);
        if (adatta) {
            adattaAUnaPagina(formato);
        } else {
            ripristinaAdattamento();
        }
        // Se window.print() viene chiamato nello stesso ciclo in cui abbiamo appena
        // cambiato classi/stili, il browser potrebbe non aver ancora dipinto un frame con
        // il nuovo layout: su iOS/Safari in particolare l'anteprima di stampa nativa puo'
        // essere generata sullo stato precedente, ignorando lo scaling di "adatta a 1
        // pagina" appena applicato. Il doppio requestAnimationFrame garantisce che almeno
        // un ciclo di paint sia avvenuto prima di aprire il foglio di stampa.
        requestAnimationFrame(function () {
            requestAnimationFrame(function () {
                window.print();
            });
        });
    }

    window.stampaAllenamento = stampaAllenamento;

    // L'evento "afterprint" non e' affidabile su tutti i dispositivi (es. il dialogo di
    // stampa nativo di Android non lo scatena sempre): ripristiniamo il layout normale
    // con piu' meccanismi di sicurezza, cosi' non restano stili residui che rompono il
    // resto della pagina.
    // NB: niente listener su "focus". Su iOS Safari la comparsa del foglio di stampa
    // nativo scatena un "focus" spurio sulla finestra pochi istanti dopo window.print():
    // se a quel punto ripristiniamo lo zoom/scala di "adatta a 1 pagina", l'anteprima di
    // stampa viene generata con il layout a piena altezza non scalato, mostrando piu'
    // pagine anche quando l'utente ha scelto "adatta a 1 pagina".
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
