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
  - **Indirizzo di broadcast**: indirizzo/i di broadcast usato/i per individuare gli apparecchi, separati da virgole. Il valore predefinito `255.255.255.255` va bene nella maggior parte dei casi. Se gli apparecchi non vengono trovati, indica l'indirizzo di broadcast della tua rete (ad esempio `192.168.1.255`).
  - **Intervallo di interrogazione predefinito**: tempo in secondi tra due letture dello stato degli apparecchi (30 s per impostazione predefinita, minimo 10 s).
- **Demone**
  - **Porta del demone**: porta locale usata dal demone (55114 per impostazione predefinita). Modificala solo in caso di conflitto con un altro plugin.

## Aggiunta degli apparecchi

Nella pagina del plugin, il pulsante **Sincronizza** recupera gli apparecchi dell'account MSmartHome, li cerca sulla rete locale e crea i dispositivi corrispondenti.

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
- **Opzioni**
  - **Intervallo di interrogazione**: lascia vuoto per usare il valore della configurazione del plugin.
- **Informazioni**
  - Numero di serie e modello dell'apparecchio, in sola lettura.

> **Importante**
>
> Conserva il *token* e la *key* dei tuoi apparecchi V3 in un luogo sicuro. Permettono di continuare a controllare gli apparecchi anche se il cloud Midea non è più disponibile.

## Comandi

I comandi vengono creati automaticamente in base alle funzionalità comunicate da ciascun apparecchio. Il loro elenco dettagliato sarà aggiunto qui non appena saranno disponibili.

## Crediti

Il plugin si basa sulle librerie open source [msmart-ng](https://github.com/mill1000/midea-msmart) e [midea-local](https://github.com/midea-lan/midea-local).
