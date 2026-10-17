# Plugin Midea MSmart

> **Plugin in fase di sviluppo**: questa documentazione descrive lo stato attuale del plugin e sarà completata a ogni versione.

## Presentazione

Il plugin **Midea MSmart** permette di controllare **in locale** i climatizzatori e i deumidificatori Midea e dei marchi associati (Comfee, Inventor, Qlima…) compatibili con l'app **MSmartHome**.

L'account MSmartHome serve solo a:

- elencare gli apparecchi associati all'account;
- recuperare una sola volta le chiavi di autenticazione (*token* e *key*) degli apparecchi recenti (protocollo V3).

In seguito, tutti i comandi e le letture di stato passano direttamente dalla rete locale, senza il cloud Midea.

Apparecchi supportati:

| Tipo | Apparecchio |
|---|---|
| `0xAC` | Climatizzatore (split, portatile, PortaSplit…) |
| `0xCC` | Climatizzatore commerciale |
| `0xA1` | Deumidificatore |

## Prerequisiti

- Jeedom 4.5 o superiore, su Debian 12 o 13.
- Gli apparecchi e Jeedom devono trovarsi sulla **stessa rete locale** (stessa sottorete) affinché il rilevamento funzioni.
- Un account **MSmartHome** su cui gli apparecchi sono **associati direttamente**. Un apparecchio solo *condiviso* da un altro account non permette di recuperarne le chiavi.

> **Consiglio**
>
> Usa preferibilmente una password composta solo da lettere e cifre.
> Dopo diversi tentativi di accesso falliti, il cloud Midea blocca temporaneamente l'account, da alcuni minuti fino a 24 ore (errori `7610` o `65027`). In tal caso, attendi prima di riprovare.

## Configurazione del plugin

Dopo l'installazione, attiva il plugin e avvia l'installazione delle dipendenze. Il plugin installa il proprio ambiente Python, isolato dal sistema.

### Dipendenze

L'installazione delle dipendenze, avviata dalla pagina di configurazione del plugin, installa solo nella cartella del plugin:

- un **Python 3.13** autonomo, scaricato con lo strumento [uv](https://github.com/astral-sh/uv), indipendentemente dalla versione di Python del sistema;
- un ambiente virtuale (`resources/python_venv`) con le librerie del plugin, in versioni fissate e verificate tramite impronta.

L'installazione richiede alcuni minuti e occupa circa 130 MB. Su un sistema a 32 bit (Raspberry Pi in `armhf`) viene installato anche un compilatore e l'operazione è più lunga, perché una libreria deve essere compilata.

Dopo un aggiornamento del plugin che modifica queste versioni, le dipendenze tornano allo stato *NOK*: basta rilanciarne l'installazione. Non sono incluse nei backup di Jeedom; dopo un ripristino, rilanciane l'installazione.

### Parametri

![Configurazione del plugin](../images/plugin_config.png)

- **Account MSmartHome**
  - **Nome utente (email)** e **Password** dell'account MSmartHome.
- **Rete locale**
  - **Indirizzo di broadcast**: indirizzo/i di broadcast usato/i per individuare gli apparecchi, separati da virgole. Lascia vuoto (predefinito) per trasmettere su tutte le interfacce di rete di Jeedom. Se gli apparecchi non vengono trovati, indica l'indirizzo di broadcast della loro rete (ad esempio `192.168.1.255`).
  - **Intervallo di interrogazione predefinito**: tempo in secondi tra due letture dello stato degli apparecchi (30 s per impostazione predefinita, minimo 10 s).
  - **Durata delle connessioni**: i climatizzatori vengono ricollegati dopo questo intervallo (90 s per impostazione predefinita). Alcuni apparecchi chiudono da soli la connessione dopo un po', causando errori e interruzioni: un valore inferiore a quell'intervallo li evita. 0 = connessione mantenuta indefinitamente.
- **Demone**
  - **Porta del demone**: porta locale usata dal demone (55114 per impostazione predefinita). Modificala solo in caso di conflitto con un altro plugin.

### Demone

Il demone gestisce la comunicazione locale con gli apparecchi. Una volta installate le dipendenze, si avvia automaticamente (gestione automatica attiva), oppure con il pulsante **(Ri)Avvia** della pagina di configurazione del plugin.

- Ascolta solo sulla macchina Jeedom (`127.0.0.1`), sulla porta definita sopra.
- **Non** si connette **mai** al cloud Midea all'avvio, il che evita i blocchi dell'account.
- I suoi messaggi sono nel log `mideamsmart_daemon`, quelli dell'installazione delle dipendenze in `mideamsmart_update`. Imposta il livello di log del plugin su *Debug* per ottenere il dettaglio degli scambi. Il plugin vi nasconde password, *token* e *key*.

## Aggiunta degli apparecchi

Nella pagina del plugin, il pulsante **Sincronizza** (il demone deve essere avviato):

1. cerca gli apparecchi sulla rete locale;
2. se è configurato un account MSmartHome, vi si connette e recupera l'elenco degli apparecchi dell'account;
3. per ogni apparecchio V3 le cui chiavi non sono ancora note, recupera il *token* e la *key* dal cloud, poi **li verifica direttamente con l'apparecchio** prima di salvarli;
4. crea i nuovi dispositivi, oppure aggiorna l'indirizzo IP, la porta e il protocollo di quelli esistenti. I nomi e le chiavi già presenti non vengono mai modificati.

Un messaggio riassume l'operazione e segnala gli apparecchi per i quali non è stato possibile ottenere le chiavi. Gli apparecchi di un tipo non supportato vengono ignorati. Senza account MSmartHome viene effettuata solo la ricerca locale.

![Pagina del plugin](../images/plugin_devices.png)

Il pulsante **Aggiungi** permette di creare un dispositivo manualmente, ad esempio per un apparecchio situato in un'altra sottorete. In questo caso devi indicare tu stesso l'identificativo, l'indirizzo IP e, per un apparecchio V3, il *token* e la *key*.

## Dispositivo

![Dispositivo](../images/device_config.png)

- **Apparecchio Midea**
  - **Tipo di apparecchio**: climatizzatore, climatizzatore commerciale o deumidificatore.
  - **Identificativo dell'apparecchio**: identificativo Midea, compilato automaticamente durante la sincronizzazione.
- **Connessione locale**
  - **Indirizzo IP** e **Porta** (6444 per impostazione predefinita).
  - **Versione del protocollo**: V3 per la maggior parte degli apparecchi recenti, V2 per quelli più vecchi.
  - **Token** e **Key**: chiavi di autenticazione degli apparecchi V3, recuperate automaticamente.
  - **Recupera token/key dal cloud**: richiede di nuovo al cloud le chiavi di questo apparecchio e le verifica, ad esempio dopo un reset del modulo Wi-Fi. Salva il dispositivo prima di usarlo.
- **Opzioni**
  - **Intervallo di interrogazione**: lascia vuoto per usare il valore della configurazione del plugin.
  - **Durata della connessione** (climatizzatori): lascia vuoto per usare il valore della configurazione del plugin.
  - **Bip di conferma**: l'apparecchio emette un bip a ogni comando ricevuto.
  - **Passo del setpoint** (climatizzatori): 1 °C o 0,5 °C.
  - **Consumo elettrico** (climatizzatori): crea i comandi di potenza e consumo. Se i valori sono incoerenti, cambia il **formato** (BCD o binario) o il **fattore di scala**.
- **Informazioni**
  - Numero di serie e modello dell'apparecchio, in sola lettura.
  - **Funzionalità**: *Ricevute dall'apparecchio*, oppure *Predefinite* se l'apparecchio non le ha ancora inviate. In tal caso vengono richieste di nuovo automaticamente, e i comandi vengono adattati appena ricevute.

> **Importante**
>
> Conserva il *token* e la *key* dei tuoi apparecchi V3 in un luogo sicuro. Permettono di continuare a controllare gli apparecchi anche se il cloud Midea non è più disponibile.

## Comandi

![Widget del climatizzatore e del deumidificatore](../images/dashboard_ac.png) ![](../images/dashboard_a1.png)

![Scheda Comandi](../images/device_commands.png)

I comandi vengono creati automaticamente **in base alle funzionalità comunicate da ciascun apparecchio**, non appena risponde per la prima volta. Se l'apparecchio non restituisce le sue funzionalità, vengono usate quelle predefinite e la richiesta viene ripetuta ogni 10 minuti.

I comandi info di tipo testo contengono un **codice stabile**, indipendente dalla lingua (ad esempio `cool`): usa questi codici negli scenari. I comandi action associati propongono etichette tradotte. Le info già mostrate da un'azione collegata sono nascoste per impostazione predefinita.

Il pulsante **Aggiorna i comandi** della scheda *Comandi* aggiunge i comandi mancanti, rimuove quelli delle funzioni che l'apparecchio non dichiara più, poi rilegge le sue funzionalità. I nomi e le impostazioni dei comandi esistenti vengono mantenuti.

| Identificativo logico | Apparecchi | Contenuto |
|---|---|---|
| `power`, `on`, `off` | AC, CC, A1 | Stato (0/1), accendi, spegni |
| `mode`, `setMode` | AC, CC | Modalità: `auto`, `cool`, `dry`, `smart_dry`, `heat`, `fan_only` (CC: `fan`). Scegliere una modalità accende l'apparecchio |
| `targetTemperature`, `setTargetTemperature` | AC, CC | Setpoint in °C, con i limiti dell'apparecchio e il passo scelto nel dispositivo |
| `indoorTemperature`, `outdoorTemperature` | AC, CC | Temperature interna ed esterna |
| `fanSpeed`, `setFanSpeed` | AC, CC | Ventilazione: `auto`, `silent`, `low`, `medium`, `high`, `max`, `custom` (CC: da `l1` a `l7`, `auto`) |
| `fanSpeedPercent`, `setFanSpeedPercent` | AC | Velocità libera da 1 a 100 %, se l'apparecchio la supporta |
| `swingMode`, `setSwingMode` | AC, CC | Oscillazione: `off`, `vertical`, `horizontal`, `both` |
| `horizontalSwingAngle`, `verticalSwingAngle` + `set…` | AC, CC | Posizione dei deflettori: `off`/`close`, da `pos_1` a `pos_5`, `auto` |
| `preset`, `setPreset` | AC, CC | Preimpostazione esclusiva: `none`, `sleep`, `freeze_protection`, `eco`, `ieco`, `turbo` (CC: `none`, `eco`, `silent`, `sleep`) |
| `breezeMode`, `setBreezeMode` | AC | Modalità Breeze: `off`, `breeze_away`, `breeze_mild`, `breezeless` |
| `indoorHumidity`, `targetHumidity`, `setTargetHumidity` | AC, CC | Umidità interna e setpoint di umidità (%) |
| `displayOn`, `toggleDisplay` | AC | Stato del display e commutazione |
| `purifier`, `purifierOn`, `purifierOff` / `purifierMode`, `setPurifierMode` | AC / CC | Purificatore (AC: acceso/spento; CC: `off`, `on`, `auto`) |
| `flash`, `outSilent`, `cascadeMode`, `freshAirFanSpeed`, `rateSelect`, `auxMode` + actions | AC (CC : `auxMode`) | Funzioni avanzate, a seconda del modello |
| `selfCleanActive`, `startSelfClean`, `filterAlert`, `defrostActive`, `errorCode` | AC | Autopulizia, avviso filtro, sbrinamento, codice errore |
| `realTimePower`, `currentEnergy`, `totalEnergy` | AC | Potenza (W) e consumi (kWh), se l'opzione *Consumo elettrico* è selezionata |
| `mode`, `setMode` | A1 | Modalità: `manual`, `continuous`, `auto`, `clothes_dry`, `shoes_dry`, `silent`. Scegliere una modalità accende l'apparecchio |
| `fanSpeed`, `setFanSpeed` | A1 | Ventilazione: `lowest`, `low`, `medium`, `high`, `auto` |
| `currentHumidity`, `currentTemperature`, `targetHumidity`, `setTargetHumidity` | A1 | Umidità e temperatura ambiente, setpoint di umidità da 35 a 85 % |
| `tankLevel`, `tankFull`, `waterLevelSet`, `setWaterLevelSet` | A1 | Livello del serbatoio (%), serbatoio pieno, soglia del serbatoio (`25`, `50`, `75`, `100`) |
| `swing`, `childLock`, `anion`, `pump` + `…On`, `…Off` | A1 | Oscillazione, blocco bambini, ionizzatore, pompa (se l'apparecchio ne ha una) |
| `filterCleaningReminder`, `resetFilter` | A1 | Promemoria di pulizia del filtro e suo azzeramento |
| `online`, `refresh` | AC, CC, A1 | Apparecchio raggiungibile (0/1) e aggiornamento immediato |

## Diagnostica e affidabilità

![Diagnostica](../images/device_diagnostic.png)

- **Diagnostica** (pulsante in alto nella pagina del dispositivo): mostra la configurazione vista da Jeedom e lo stato visto dal demone (connessione, ultima risposta, ultimo errore, funzionalità e valori grezzi dell'apparecchio). Il pulsante **Copia per il forum** copia questo riepilogo, senza password, *token* né *key*, pronto da incollare in una richiesta di aiuto sul [forum Jeedom](https://community.jeedom.com).
- **Apparecchio non raggiungibile**: il comando `online` passa a 0 e il dispositivo viene segnalato in *timeout* in Jeedom. Le interrogazioni vengono progressivamente diradate, fino a una ogni 5 minuti, poi riprendono il ritmo normale non appena l'apparecchio risponde.
- **Cambio di indirizzo IP**: se un apparecchio non risponde da 5 minuti, il demone lo cerca sulla rete locale (al massimo una volta ogni 10 minuti, senza cloud). Se lo trova a un altro indirizzo, l'indirizzo IP del dispositivo viene aggiornato automaticamente. È comunque consigliato riservare l'indirizzo dei tuoi apparecchi nel router.
- **Protezione dell'account MSmartHome**: un blocco del cloud (codici `7610`, `65027`) o una password rifiutata vengono memorizzati, anche dopo un riavvio del demone. Durante un blocco, la sincronizzazione si limita alla rete locale e il recupero delle chiavi viene rifiutato. Una password rifiutata non viene più provata finché non viene modificata.
- **Pagina Salute** di Jeedom: indica il numero di apparecchi raggiungibili e lo stato dell'account MSmartHome.

## Risoluzione dei problemi

| Messaggio | Soluzione |
|---|---|
| *Network error … Transport is closing or closed* (warning) | L'apparecchio ha chiuso la connessione: il plugin si ricollega e ripete subito la richiesta. Se il messaggio è frequente, riduci la **durata delle connessioni** (ad esempio 60 s). |
| *Payload … failed CRC and checksum* (warning) | Frame non valido ignorato dalla libreria, spesso legato a interruzioni della connessione: stessa soluzione di sopra. |
| Comandi in più, o diversi tra apparecchi identici | Le funzionalità non sono state ricevute (indicatore *Funzionalità* del dispositivo): vengono richieste di nuovo automaticamente. Puoi anche fare clic su **Aggiorna i comandi**. |
| *Nome utente o password MSmartHome errati* | Verifica l'account nella configurazione del plugin. Il plugin non riprova finché le credenziali non cambiano. |
| *Il cloud Midea ha bloccato temporaneamente l'account* | Troppe connessioni (codici `7610`, `65027`). Attendi il tempo indicato senza avviare un'altra sincronizzazione. |
| *apparecchio non associato direttamente a questo account (condiviso?)* | Nell'app MSmartHome, associa l'apparecchio a questo account, non solo tramite condivisione. |
| *apparecchio assente dall'account MSmartHome* | L'apparecchio è sulla rete ma in un altro account: inserisci *token* e *key* manualmente, oppure associalo a questo account. |
| *chiavi rifiutate dall'apparecchio* | Rilancia **Recupera token/key dal cloud**; se il problema persiste, associa di nuovo l'apparecchio nell'app. |
| *apparecchio non trovato sulla rete locale* / *non raggiungibile* | Verifica che l'apparecchio sia acceso e sulla stessa rete di Jeedom, oppure indica l'**indirizzo di broadcast** della sua rete. |

## Crediti

Il plugin si basa sulle librerie open source [msmart-ng](https://github.com/mill1000/midea-msmart) e [midea-local](https://github.com/midea-lan/midea-local).

Il plugin è ideato e diretto da **ddelec24** (direttore d'orchestra del progetto) e sviluppato con **Claude** (Anthropic), coautore del codice e della documentazione.
