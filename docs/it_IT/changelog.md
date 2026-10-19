# Changelog del plugin Midea MSmart

>**IMPORTANT**
>
>Se non ci sono informazioni sull'aggiornamento, significa che riguarda solo l'aggiornamento della documentazione, della traduzione o del testo.

# 19/10/2026

- Versione beta 0.10.0
- Nuova **programmazione** oraria: profili comuni a tutti gli apparecchi (*Normale* e *Vacanze* per impostazione predefinita, modificabili), fasce proprie di ogni apparecchio (giorni, ora, accendere o spegnere, modalità, setpoint, ventilazione, preimpostazione o umidità)
- Nuovo dispositivo *Programmazione*, aperto dal riquadro omonimo: il suo comando *Scegli il profilo* cambia tutti gli apparecchi in un colpo solo, per esempio da uno scenario delle vacanze
- Recupero dell'ultima fascia passata al cambio di profilo, alla ripresa della programmazione o al riavvio di Jeedom (disattivabile per apparecchio)
- Nuovi comandi *Segui la programmazione* e *Sospendi la programmazione* su ogni apparecchio
- Deumidificatore: più comandi inviati di seguito (per esempio modalità poi umidità) non si annullano più a vicenda

# 17/10/2026

- Versione beta 0.9.2
- Correzione del pulsante **Copia per il forum** della diagnostica quando Jeedom è aperto in HTTP sulla rete locale. Se il browser rifiuta la copia, il testo viene mostrato, selezionato, per copiarlo a mano
- Data dell'ultima comunicazione del dispositivo aggiornata a ogni interrogazione riuscita, anche quando nessun valore cambia: il *ritardo massimo tra due comunicazioni* di Jeedom non segnala più il dispositivo per errore
- Comando *Sbrinamento in corso* creato solo se l'apparecchio comunica questa informazione. Per rimuovere quello già creato, clicca su **Aggiorna i comandi**
- Diagnostica completata: durata delle connessioni e stato della richiesta delle funzionalità
- Versione beta 0.9.1
- Crediti: autori del plugin specificati (ddelec24, direttore d'orchestra; Claude, coautore) nella documentazione, nella licenza e nella scheda del plugin
- Nuova opzione **Durata delle connessioni** (90 s per impostazione predefinita), rimedio per gli apparecchi che chiudono da soli la connessione (errori *Transport is closing or closed* e *failed CRC and checksum*)
- Richiesta o comando inviato di nuovo una volta su una nuova connessione quando l'apparecchio chiude la connessione, e apparecchio dichiarato offline solo dopo due errori consecutivi
- Questi errori della libreria sono registrati come warning
- Funzionalità richieste di nuovo rapidamente se l'apparecchio non le ha inviate, con adattamento automatico dei comandi alla loro ricezione (comandi in più, come *Filtro da pulire*, su un solo apparecchio)
- Indicatore dello stato delle funzionalità nella pagina del dispositivo
- Correzione di un errore all'arresto di un deumidificatore

# 16/10/2026

- Prima versione beta (0.9.0), da provare con apparecchi reali: i tuoi riscontri sono benvenuti sul forum
- Creazione del plugin: struttura di base, pagina di configurazione e pagina dei dispositivi
- Installazione delle dipendenze: Python 3.13 autonomo (tramite uv) e ambiente virtuale dedicato al plugin
- Demone Python (asyncio): avvio, arresto pulito, comunicazione con Jeedom e trasmissione dell'elenco dei dispositivi
- Sincronizzazione degli apparecchi: account MSmartHome, ricerca sulla rete locale, creazione e aggiornamento dei dispositivi
- Recupero del token e della key, verificati con l'apparecchio, e pulsante per richiederli di nuovo
- Protezione contro il blocco dell'account Midea (codici 7610 e 65027)
- Indirizzo di broadcast automatico per impostazione predefinita (tutte le interfacce di rete)
- Controllo locale dei climatizzatori (AC) e climatizzatori commerciali (CC) con msmart-ng: stato, interrogazione periodica, apparecchio offline
- Comandi creati in base alle funzionalità di ogni apparecchio, con codici stabili per gli scenari e pulsante di aggiornamento
- Opzioni del dispositivo: bip, passo del setpoint, consumo elettrico
- Controllo locale dei deumidificatori (A1) con midea-local: modalità, ventilazione, setpoint di umidità, serbatoio, oscillazione, ionizzatore, pompa, blocco bambini, filtro
- Avvisi serbatoio pieno e filtro mostrati con un'icona verde o rossa
- Finestra di diagnostica per dispositivo, con copia di un riepilogo senza segreti per il forum
- Ricerca automatica sulla rete locale degli apparecchi che hanno cambiato indirizzo IP
- Blocchi del cloud e password rifiutata memorizzati, anche dopo un riavvio del demone
- Dispositivo segnalato in timeout quando l'apparecchio non risponde più, pagina Salute e informazioni per il forum
