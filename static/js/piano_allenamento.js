// Builder del piano di allenamento a fasi (creazione/modifica allenamento).
// Ogni fase contiene dei "blocchi" di serie: un blocco raggruppa le serie che vanno
// ripetute insieme (es. "x2"). Si aspetta nella pagina: window.FASI_TIPI = [[codice, nome], ...],
// window.PIANO_INIZIALE = [fase, ...] (fase.blocchi = [{ripetizioni, righe}, ...]),
// un form con id "form-allenamento", un contenitore #piano-builder, un pulsante
// #piano-aggiungi-fase, un input nascosto #piano-json-input e, facoltativo, un elemento
// #piano-volume-totale dove viene mostrato il volume totale calcolato man mano.
(function () {
    var contenitore = document.getElementById("piano-builder");
    var bottoneAggiungiFase = document.getElementById("piano-aggiungi-fase");
    var form = document.getElementById("form-allenamento");
    var inputNascosto = document.getElementById("piano-json-input");
    var elementoVolumeTotale = document.getElementById("piano-volume-totale");
    if (!contenitore || !form || !inputNascosto) return;

    var FASI_TIPI = window.FASI_TIPI || [];
    // codice -> colore (stessa regola usata per l'header della fase nella vista di sola
    // lettura/PDF, vedi fase_colore() in piani_allenamento.py): qui colora anche la
    // casella "Tipo" e il contorno dell'intera fase nel builder, cosi' si distinguono
    // a colpo d'occhio blocchi e serie appartenenti alla stessa fase.
    var FASI_TIPI_COLORE = {};
    FASI_TIPI.forEach(function (t) { FASI_TIPI_COLORE[t[0]] = t[2]; });

    function applicaColoreFase(selectTipo, card) {
        var colore = FASI_TIPI_COLORE[selectTipo.value] || FASI_TIPI_COLORE.altro;
        if (!colore) return;
        card.style.borderColor = colore;
        selectTipo.style.background = colore;
        selectTipo.style.borderColor = colore;
        selectTipo.style.color = "#fff";
    }

    // Una "serie" e' una singola <tr>: serie / esercizio (testo anche lungo, va a capo) /
    // recupero / ripartenza / rimuovi. Le ripetizioni si impostano una volta sola a livello
    // di blocco (vedi creaBlocco), non per singola serie.
    function creaRiga(riga) {
        riga = riga || {};
        var tr = document.createElement("tr");

        var tdSerie = document.createElement("td");
        var inputSerie = document.createElement("input");
        inputSerie.type = "text";
        inputSerie.className = "riga-serie";
        inputSerie.placeholder = "es. 4 x 50 m";
        inputSerie.value = riga.serie || "";
        tdSerie.appendChild(inputSerie);
        tr.appendChild(tdSerie);

        var tdEsercizio = document.createElement("td");
        var textareaEsercizio = document.createElement("textarea");
        textareaEsercizio.className = "riga-esercizio";
        textareaEsercizio.rows = 2;
        textareaEsercizio.placeholder = "Descrizione dell'esercizio (anche un testo lungo)";
        textareaEsercizio.value = riga.esercizio || "";
        tdEsercizio.appendChild(textareaEsercizio);
        tr.appendChild(tdEsercizio);

        [
            ["recupero", riga.recupero, 'es. 15"'],
            ["ripartenza", riga.ripartenza, "es. 1'10\""],
        ].forEach(function (campo) {
            var td = document.createElement("td");
            var input = document.createElement("input");
            input.type = "text";
            input.className = "riga-" + campo[0];
            input.value = campo[1] || "";
            input.placeholder = campo[2];
            td.appendChild(input);
            tr.appendChild(td);
        });

        var tdBtn = document.createElement("td");
        var btnRimuovi = document.createElement("button");
        btnRimuovi.type = "button";
        btnRimuovi.className = "fase-riga-rimuovi";
        btnRimuovi.title = "Rimuovi serie";
        btnRimuovi.textContent = "✖";
        btnRimuovi.addEventListener("click", function () { tr.remove(); });
        tdBtn.appendChild(btnRimuovi);
        tr.appendChild(tdBtn);

        return tr;
    }

    function creaBlocco(blocco) {
        blocco = blocco || {};
        var wrap = document.createElement("div");
        wrap.className = "fase-blocco-builder";

        var head = document.createElement("div");
        head.className = "fase-blocco-head";

        var campoRip = document.createElement("div");
        campoRip.innerHTML = "<label>Ripetizioni blocco</label>";
        var inputRip = document.createElement("input");
        inputRip.type = "text";
        inputRip.className = "blocco-ripetizioni";
        inputRip.placeholder = "es. x2, x3 — vuoto se una sola volta";
        inputRip.value = blocco.ripetizioni || "";
        campoRip.appendChild(inputRip);
        head.appendChild(campoRip);

        var btnRimuoviBlocco = document.createElement("button");
        btnRimuoviBlocco.type = "button";
        btnRimuoviBlocco.className = "btn-danger fase-rimuovi";
        btnRimuoviBlocco.title = "Rimuovi blocco";
        btnRimuoviBlocco.textContent = "✖ Rimuovi blocco";
        btnRimuoviBlocco.addEventListener("click", function () {
            if (window.confirm("Rimuovere questo blocco di serie?")) wrap.remove();
        });
        head.appendChild(btnRimuoviBlocco);
        wrap.appendChild(head);

        // Sullo schermo del telefono la tabella non va mai a capo/schiacciata: se non
        // entra nello spazio disponibile si scorre in orizzontale, come nella vista di
        // sola lettura dell'allenamento (vedi .fase-table-scroll in style.css).
        var hint = document.createElement("p");
        hint.className = "fase-table-hint";
        hint.hidden = true;
        hint.innerHTML = "&harr; Scorri orizzontalmente per vedere tutte le colonne";
        wrap.appendChild(hint);

        var scrollWrap = document.createElement("div");
        scrollWrap.className = "fase-table-scroll";

        var table = document.createElement("table");
        table.className = "table fase-builder-righe-table";
        table.innerHTML =
            "<thead><tr><th>Serie</th><th>Esercizio</th><th>Recupero</th><th>Tempo di ripartenza</th><th></th></tr></thead>";
        var tbody = document.createElement("tbody");
        tbody.className = "blocco-righe-body";
        (blocco.righe || []).forEach(function (riga) { tbody.appendChild(creaRiga(riga)); });
        if (!(blocco.righe && blocco.righe.length)) tbody.appendChild(creaRiga());
        table.appendChild(tbody);
        scrollWrap.appendChild(table);
        wrap.appendChild(scrollWrap);

        var btnAggiungiRiga = document.createElement("button");
        btnAggiungiRiga.type = "button";
        btnAggiungiRiga.className = "btn";
        btnAggiungiRiga.style.marginTop = "6px";
        btnAggiungiRiga.textContent = "+ Aggiungi serie al blocco";
        btnAggiungiRiga.addEventListener("click", function () {
            tbody.appendChild(creaRiga());
            aggiornaScrollTabelle();
        });
        wrap.appendChild(btnAggiungiRiga);

        return wrap;
    }

    function creaFase(fase) {
        fase = fase || {};
        var card = document.createElement("div");
        card.className = "card fase-builder-card";

        var head = document.createElement("div");
        head.className = "fase-builder-head";

        var campoTipo = document.createElement("div");
        campoTipo.innerHTML = "<label>Tipo</label>";
        var selectTipo = document.createElement("select");
        selectTipo.className = "fase-tipo";
        FASI_TIPI.forEach(function (t) {
            var opt = document.createElement("option");
            opt.value = t[0];
            opt.textContent = t[1];
            if (fase.tipo === t[0]) opt.selected = true;
            selectTipo.appendChild(opt);
        });
        campoTipo.appendChild(selectTipo);
        head.appendChild(campoTipo);
        applicaColoreFase(selectTipo, card);

        var campoNome = document.createElement("div");
        campoNome.innerHTML = "<label>Nome fase</label>";
        var inputNome = document.createElement("input");
        inputNome.type = "text";
        inputNome.className = "fase-nome";
        inputNome.placeholder = "es. Riscaldamento";
        inputNome.value = fase.nome || "";
        campoNome.appendChild(inputNome);
        head.appendChild(campoNome);

        selectTipo.addEventListener("change", function () {
            if (!inputNome.value.trim() || FASI_TIPI.some(function (t) { return t[1] === inputNome.value; })) {
                var scelto = FASI_TIPI.find(function (t) { return t[0] === selectTipo.value; });
                if (scelto) inputNome.value = scelto[1];
            }
            applicaColoreFase(selectTipo, card);
        });

        var campoDurata = document.createElement("div");
        campoDurata.innerHTML = "<label>Durata (min)</label>";
        var inputDurata = document.createElement("input");
        inputDurata.type = "number";
        inputDurata.min = "0";
        inputDurata.className = "fase-durata";
        inputDurata.value = fase.durata_min != null ? fase.durata_min : "";
        campoDurata.appendChild(inputDurata);
        head.appendChild(campoDurata);

        var campoMetri = document.createElement("div");
        campoMetri.innerHTML = "<label>Volume (m)</label>";
        var inputMetri = document.createElement("input");
        inputMetri.type = "number";
        inputMetri.min = "0";
        inputMetri.className = "fase-metri";
        inputMetri.readOnly = true;
        inputMetri.title = "Calcolato automaticamente dalla colonna Serie dei blocchi";
        inputMetri.value = fase.metri != null ? fase.metri : "";
        campoMetri.appendChild(inputMetri);
        head.appendChild(campoMetri);

        var campoRimuovi = document.createElement("div");
        var btnRimuoviFase = document.createElement("button");
        btnRimuoviFase.type = "button";
        btnRimuoviFase.className = "btn-danger fase-rimuovi";
        btnRimuoviFase.title = "Rimuovi fase";
        btnRimuoviFase.textContent = "✖ Rimuovi fase";
        btnRimuoviFase.addEventListener("click", function () {
            if (window.confirm("Rimuovere questa fase dal piano?")) card.remove();
        });
        campoRimuovi.appendChild(btnRimuoviFase);
        head.appendChild(campoRimuovi);

        card.appendChild(head);

        var labelSotto = document.createElement("label");
        labelSotto.textContent = "Attrezzi richiesti:";
        card.appendChild(labelSotto);
        var inputSotto = document.createElement("input");
        inputSotto.type = "text";
        inputSotto.className = "fase-sottotitolo";
        inputSotto.placeholder = "es. Tavoletta, pull buoy, elastico";
        inputSotto.value = fase.sottotitolo || "";
        card.appendChild(inputSotto);

        var labelBlocchi = document.createElement("label");
        labelBlocchi.style.marginBottom = "0";
        labelBlocchi.textContent = "Blocchi di serie";
        card.appendChild(labelBlocchi);
        var pAiutoBlocchi = document.createElement("p");
        pAiutoBlocchi.innerHTML =
            "<small>Un blocco raggruppa le serie da ripetere insieme (es. \"x2\": tavoletta + catch-up, " +
            "ripetute due volte di seguito). Lascia \"Ripetizioni blocco\" vuoto per una serie singola.</small>";
        card.appendChild(pAiutoBlocchi);

        var blocchiContenitore = document.createElement("div");
        blocchiContenitore.className = "fase-blocchi";
        (fase.blocchi || []).forEach(function (blocco) { blocchiContenitore.appendChild(creaBlocco(blocco)); });
        card.appendChild(blocchiContenitore);
        if (!(fase.blocchi && fase.blocchi.length)) blocchiContenitore.appendChild(creaBlocco());

        var btnAggiungiBlocco = document.createElement("button");
        btnAggiungiBlocco.type = "button";
        btnAggiungiBlocco.className = "btn";
        btnAggiungiBlocco.style.marginTop = "8px";
        btnAggiungiBlocco.textContent = "+ Aggiungi serie";
        btnAggiungiBlocco.addEventListener("click", function () {
            blocchiContenitore.appendChild(creaBlocco());
            aggiornaScrollTabelle();
        });
        card.appendChild(btnAggiungiBlocco);

        var labelNota = document.createElement("label");
        labelNota.textContent = "Nota (facoltativa)";
        card.appendChild(labelNota);
        var textareaNota = document.createElement("textarea");
        textareaNota.className = "fase-nota";
        textareaNota.rows = 2;
        textareaNota.value = fase.nota || "";
        card.appendChild(textareaNota);

        return card;
    }

    // Ricalcola ombre/hint di scorrimento orizzontale delle tabelle del builder
    // (window.FaseTableScroll e' definito da fase_table_scroll.js, incluso in pagina).
    function aggiornaScrollTabelle() {
        if (window.FaseTableScroll) window.FaseTableScroll.aggiorna();
    }

    // Interpreta il testo di una cella "Serie" come un prodotto di numeri separati da
    // "x"/"X" (es. "2x100" o "2 X 100" => 200; "4x50 m" => 200, ignorando l'unita').
    // Spazi e lettere non numeriche vengono ignorati; un solo numero vale per se' stesso.
    function parseValoreSerie(testo) {
        if (!testo) return 0;
        var pulito = testo.replace(/\s+/g, "");
        var numeri = pulito.split(/[xX]/).map(function (parte) {
            var m = parte.match(/\d+(?:[.,]\d+)?/);
            return m ? parseFloat(m[0].replace(",", ".")) : null;
        }).filter(function (n) { return n !== null; });
        if (!numeri.length) return 0;
        return numeri.reduce(function (a, b) { return a * b; }, 1);
    }

    // Interpreta il moltiplicatore di un blocco (es. "x2", "x3"): 1 se vuoto o non numerico.
    function parseMoltiplicatoreBlocco(testo) {
        if (!testo) return 1;
        var m = testo.replace(/\s+/g, "").match(/\d+(?:[.,]\d+)?/);
        if (!m) return 1;
        var n = parseFloat(m[0].replace(",", "."));
        return (!n || n <= 0) ? 1 : n;
    }

    // Volume di lavoro di una fase: somma, per ogni blocco, delle serie del blocco
    // moltiplicata per le ripetizioni del blocco; poi somma di tutti i blocchi della fase.
    function calcolaVolumeFase(card) {
        var totale = 0;
        card.querySelectorAll(".fase-blocco-builder").forEach(function (blocco) {
            var moltiplicatore = parseMoltiplicatoreBlocco(blocco.querySelector(".blocco-ripetizioni").value);
            var sommaBlocco = 0;
            blocco.querySelectorAll(".blocco-righe-body > tr").forEach(function (tr) {
                sommaBlocco += parseValoreSerie(tr.querySelector(".riga-serie").value);
            });
            totale += sommaBlocco * moltiplicatore;
        });
        return totale;
    }

    function aggiornaVolumeFase(card) {
        var totale = calcolaVolumeFase(card);
        card.querySelector(".fase-metri").value = totale > 0 ? totale : "";
    }

    // Volume totale dell'intero allenamento: somma del volume di tutte le fasi del builder.
    function aggiornaVolumeTotale() {
        if (!elementoVolumeTotale) return;
        var totale = 0;
        contenitore.querySelectorAll(".fase-builder-card").forEach(function (card) {
            totale += calcolaVolumeFase(card);
        });
        elementoVolumeTotale.textContent = totale + " m";
    }

    function aggiornaTuttiIVolumi() {
        contenitore.querySelectorAll(".fase-builder-card").forEach(aggiornaVolumeFase);
        aggiornaVolumeTotale();
    }

    // Il volume si ricalcola da solo: digitando in una serie o nelle ripetizioni di un
    // blocco (bubbling dell'evento "input"), oppure aggiungendo/rimuovendo righe, blocchi
    // o fasi (bubbling del "click" dei relativi pulsanti, dopo che il DOM e' stato aggiornato).
    contenitore.addEventListener("input", function (e) {
        if (e.target.classList.contains("riga-serie") || e.target.classList.contains("blocco-ripetizioni")) {
            aggiornaTuttiIVolumi();
        }
    });
    contenitore.addEventListener("click", function () { aggiornaTuttiIVolumi(); });

    function aggiungiFase(fase) {
        var card = creaFase(fase);
        contenitore.appendChild(card);
        aggiornaScrollTabelle();
        aggiornaTuttiIVolumi();
    }

    function serializzaPiano() {
        var fasi = [];
        contenitore.querySelectorAll(".fase-builder-card").forEach(function (card) {
            var blocchi = [];
            card.querySelectorAll(".fase-blocco-builder").forEach(function (bloccoEl) {
                var righe = [];
                bloccoEl.querySelectorAll(".blocco-righe-body > tr").forEach(function (tr) {
                    var riga = {
                        serie: tr.querySelector(".riga-serie").value.trim(),
                        esercizio: tr.querySelector(".riga-esercizio").value.trim(),
                        recupero: tr.querySelector(".riga-recupero").value.trim(),
                        ripartenza: tr.querySelector(".riga-ripartenza").value.trim(),
                    };
                    if (riga.serie || riga.esercizio || riga.recupero || riga.ripartenza) righe.push(riga);
                });
                if (righe.length) {
                    blocchi.push({
                        ripetizioni: bloccoEl.querySelector(".blocco-ripetizioni").value.trim(),
                        righe: righe,
                    });
                }
            });

            var durataVal = card.querySelector(".fase-durata").value;
            var metriVal = card.querySelector(".fase-metri").value;
            fasi.push({
                tipo: card.querySelector(".fase-tipo").value,
                nome: card.querySelector(".fase-nome").value.trim(),
                durata_min: durataVal ? parseInt(durataVal, 10) : null,
                metri: metriVal ? parseInt(metriVal, 10) : null,
                sottotitolo: card.querySelector(".fase-sottotitolo").value.trim(),
                nota: card.querySelector(".fase-nota").value.trim(),
                blocchi: blocchi,
            });
        });
        return fasi;
    }

    bottoneAggiungiFase.addEventListener("click", function () { aggiungiFase(); });

    form.addEventListener("submit", function () {
        inputNascosto.value = JSON.stringify(serializzaPiano());
    });

    (window.PIANO_INIZIALE || []).forEach(function (fase) { aggiungiFase(fase); });
})();
