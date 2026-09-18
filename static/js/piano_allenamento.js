// Builder del piano di allenamento a fasi (creazione/modifica allenamento).
// Si aspetta nella pagina: window.FASI_TIPI = [[codice, nome], ...], window.PIANO_INIZIALE = [fase, ...],
// un form con id "form-allenamento", un contenitore #piano-builder, un pulsante #piano-aggiungi-fase
// e un input nascosto #piano-json-input.
(function () {
    var contenitore = document.getElementById("piano-builder");
    var bottoneAggiungiFase = document.getElementById("piano-aggiungi-fase");
    var form = document.getElementById("form-allenamento");
    var inputNascosto = document.getElementById("piano-json-input");
    if (!contenitore || !form || !inputNascosto) return;

    var FASI_TIPI = window.FASI_TIPI || [];

    function creaRiga(riga) {
        riga = riga || {};
        var tr = document.createElement("tr");

        [
            ["rip_blocco", riga.rip_blocco, "es. — o x3"],
            ["serie", riga.serie, "es. 4 x 50 m"],
            ["esercizio", riga.esercizio, "es. Stile libero a ritmo soglia"],
            ["recupero", riga.recupero, 'es. 15"'],
            ["ripartenza", riga.ripartenza, "es. 1'10\""],
        ].forEach(function (campo) {
            var td = document.createElement("td");
            var input = document.createElement("input");
            input.type = "text";
            input.className = "fase-riga-" + campo[0];
            input.value = campo[1] || "";
            input.placeholder = campo[2];
            td.appendChild(input);
            tr.appendChild(td);
        });

        var tdBtn = document.createElement("td");
        var btn = document.createElement("button");
        btn.type = "button";
        btn.className = "fase-riga-rimuovi";
        btn.title = "Rimuovi riga";
        btn.textContent = "✖";
        btn.addEventListener("click", function () { tr.remove(); });
        tdBtn.appendChild(btn);
        tr.appendChild(tdBtn);

        return tr;
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

        var table = document.createElement("table");
        table.className = "table fase-builder-righe-table";
        table.innerHTML =
            "<thead><tr><th>Rip. blocco</th><th>Serie</th><th>Esercizio</th><th>Recupero</th>" +
            "<th>Tempo di ripartenza</th><th></th></tr></thead>";
        var tbody = document.createElement("tbody");
        tbody.className = "fase-righe-body";
        (fase.righe || []).forEach(function (riga) { tbody.appendChild(creaRiga(riga)); });
        table.appendChild(tbody);
        card.appendChild(table);

        var btnAggiungiRiga = document.createElement("button");
        btnAggiungiRiga.type = "button";
        btnAggiungiRiga.className = "btn";
        btnAggiungiRiga.style.marginTop = "8px";
        btnAggiungiRiga.textContent = "+ Aggiungi riga";
        btnAggiungiRiga.addEventListener("click", function () { tbody.appendChild(creaRiga()); });
        card.appendChild(btnAggiungiRiga);

        var labelNota = document.createElement("label");
        labelNota.textContent = "Nota (facoltativa)";
        card.appendChild(labelNota);
        var textareaNota = document.createElement("textarea");
        textareaNota.className = "fase-nota";
        textareaNota.rows = 2;
        textareaNota.value = fase.nota || "";
        card.appendChild(textareaNota);

        if (!(fase.righe && fase.righe.length)) tbody.appendChild(creaRiga());

        return card;
    }

    function aggiungiFase(fase) {
        contenitore.appendChild(creaFase(fase));
    }

    function serializzaPiano() {
        var fasi = [];
        contenitore.querySelectorAll(".fase-builder-card").forEach(function (card) {
            var righe = [];
            card.querySelectorAll(".fase-righe-body tr").forEach(function (tr) {
                var riga = {
                    rip_blocco: tr.querySelector(".fase-riga-rip_blocco").value.trim(),
                    serie: tr.querySelector(".fase-riga-serie").value.trim(),
                    esercizio: tr.querySelector(".fase-riga-esercizio").value.trim(),
                    recupero: tr.querySelector(".fase-riga-recupero").value.trim(),
                    ripartenza: tr.querySelector(".fase-riga-ripartenza").value.trim(),
                };
                if (riga.serie || riga.esercizio || riga.rip_blocco || riga.recupero || riga.ripartenza) {
                    righe.push(riga);
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
                righe: righe,
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
