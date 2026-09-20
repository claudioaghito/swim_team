// Service worker minimale: nessuna cache (l'app richiede login, non vogliamo
// servire pagine vecchie/dati sensibili offline). Serve solo a soddisfare i
// requisiti di "app installabile" dei browser Android/Chrome.
self.addEventListener("fetch", function () {});
