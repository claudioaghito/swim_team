// Builder del piano di allenamento a fasi (creazione/modifica allenamento).
// Ogni fase contiene dei "blocchi" di serie: un blocco raggruppa le serie che vanno
// ripetute insieme (es. "x2"). Si aspetta nella pagina: window.FASI_TIPI = [[codice, nome], ...],
// window.PIANO_INIZIALE = [fase, ...] (fase.blocchi = [{ripetizioni, righe}, ...]),
// un form con id "form-allenamento", un contenitore #piano-builder, un pulsante
// #piano-aggiungi-fase e un input nascosto #piano-json-input.
(function () {
    var contenitore = document.getElementById("piano-builder");
    var bottoneAggiungiFase = document.getElementById("piano-aggiungi-fase");
    var form = document.getElementById("form-allenamento");
    var inputNascosto = document.getElementById("piano-json-input");
    if (!contenitore || !form || !inputNascosto) return;

    var FASI_TIPI = window.FASI_TIPI || [];

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

        var table = document.createElement("table");
        table.className = "table fase-builder-righe-table";
        table.innerHTML =
            "<thead><tr><th>Serie</th><th>Esercizio</th><th>Recupero</th><th>Tempo di ripartenza</th><th></th></tr></thead>";
        var tbody = document.createElement("tbody");
        tbody.className = "blocco-righe-body";
        (blocco.righe || []).forEach(function (riga) { tbody.appendChild(creaRiga(riga)); });
        if (!(blocco.righe && blocco.righe.length)) tbody.appendChild(creaRiga());
        table.appendChild(tbody);
        wrap.appendChild(table);

        var btnAggiungiRiga = document.createElement("button");
        btnAggiungiRiga.type = "button";
        btnAggiungiRiga.className = "btn";
        btnAggiungiRiga.style.marginTop = "6px";
        btnAggiungiRiga.textContent = "+ Aggiungi serie al blocco";
        btnAggiungiRiga.addEventListener("click", function () { tbody.appendChild(creaRiga()); });
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
        labelSotto.textContent = "Sottotitolo (facoltativo)";
        card.appendChild(labelSotto);
        var inputSotto = document.createElement("input");
        inputSotto.type = "text";
        inputSotto.className = "fase-sottotitolo";
        inputSotto.placeholder = "es. Attivazione cardiovascolare graduale e risveglio muscolare";
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
        btnAggiungiBlocco.textContent = "+ Aggiungi blocco di serie";
        btnAggiungiBlocco.addEventListener("click", function () { blocchiContenitore.appendChild(creaBlocco()); });
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

    function aggiungiFase(fase) {
        contenitore.appendChild(creaFase(fase));
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
