# AM Global Connect 8.6 — eventi automatici (da attivare)

## Cosa fa
- Il file HTML contiene ancora l’archivio di scuole e contatti e una fotografia degli eventi, per l’uso offline.
- Online legge `data/events.json`, aggiornato ogni giorno dal workflow `.github/workflows/events.yml`.
- Se il recupero non produce almeno 5 eventi, lo script fallisce e NON sovrascrive l’ultimo elenco.
- La data del controllo riuscito è visibile nell’app. L’HTML aperto da Downloads non può aggiornarsi da solo.
- I pin sono collocati solo per città riconosciute. Eventi con città non determinata sono visibili nell’elenco ma senza pin.
- Lo script legge date e nomi dal calendario ufficiale; città e venue sono importate solo quando esplicitamente strutturate nella pagina. Non inventa informazioni.

## Attivazione via browser (senza Terminale)
1. Crea un repository GitHub. ATTENZIONE: l’HTML contiene referenti ed email: NON pubblicarlo in un repository pubblico né su GitHub Pages senza prima rimuovere i dati personali. Per la pubblicazione serve una soluzione protetta o un HTML pubblico senza contatti.
2. Carica tutti i file e le cartelle, inclusa `.github/workflows/events.yml` (il caricamento ZIP su GitHub non estrae automaticamente il contenuto).
3. Settings → Actions → General: consenti al workflow di scrivere nel repository, se la configurazione lo richiede.
4. Actions → Aggiorna eventi Arthur Murray → Run workflow. Verifica l’esecuzione e apri `data/events.json`: `checked_at` deve essere compilato e `events` deve contenere eventi.
5. Pubblica l’app su un hosting HTTP(S) protetto che serva `index.html` e `data/events.json`. Solo così la pagina carica i dati aggiornati.

## Limiti
- Il parser dipende dalla struttura HTML del sito Arthur Murray: se cambia, può fallire. Testare la prima esecuzione e monitorare i fallimenti.
- GitHub Actions programmato può essere ritardato o saltato; non è una garanzia di esecuzione esatta ogni 24 ore.
- La mappa originale è stilizzata; i pin indicano città, non coordinate GPS dell’hotel.
- La cronologia completa degli eventi passati non è garantita dal calendario ufficiale.
- Non è stato effettuato un test end-to-end live su GitHub: l’automazione è pronta per l’attivazione, non già attiva.
