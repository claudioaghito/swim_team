// Service worker minimale: nessuna cache (l'app richiede login, non vogliamo
// servire pagine vecchie/dati sensibili offline). Serve a soddisfare i requisiti
// di "app installabile" dei browser Android/Chrome e a ricevere le notifiche push.
self.addEventListener("fetch", function () {});

self.addEventListener("push", function (event) {
    var dati = {};
    try {
        dati = event.data ? event.data.json() : {};
    } catch (e) {}

    var titolo = dati.title || "Derthona Nuoto Master";
    var opzioni = {
        body: dati.body || "",
        icon: "/static/icons/pwa/icon-192.png",
        badge: "/static/icons/pwa/icon-192.png",
        data: { url: dati.url || "/" },
    };

    event.waitUntil(
        self.registration.showNotification(titolo, opzioni).then(function () {
            // Bonus per Android/Chrome: aggiorna subito il pallino sull'icona con il
            // numero di messaggi non letti al momento dell'invio (su iOS non ha effetto,
            // l'API non esiste, ma la notifica sopra viene comunque mostrata).
            if ("setAppBadge" in navigator && typeof dati.count === "number") {
                return dati.count > 0
                    ? navigator.setAppBadge(dati.count).catch(function () {})
                    : navigator.clearAppBadge().catch(function () {});
            }
        })
    );
});

self.addEventListener("notificationclick", function (event) {
    event.notification.close();
    var url = (event.notification.data && event.notification.data.url) || "/";

    event.waitUntil(
        clients.matchAll({ type: "window", includeUncontrolled: true }).then(function (elenco) {
            for (var i = 0; i < elenco.length; i++) {
                if (elenco[i].url.indexOf(url) >= 0 && "focus" in elenco[i]) {
                    return elenco[i].focus();
                }
            }
            if (clients.openWindow) {
                return clients.openWindow(url);
            }
        })
    );
});
