# mideamsmart — Récapitulatif projet

> Document de référence du plugin, à relire avant chaque étape et à mettre à jour à chaque décision.
> Dernière mise à jour : 2026-10-16 (étapes 1 à 6 terminées)

## 1. Contexte

- Refonte complète, sans reprise de code, de l'ancien plugin `mideawifi`. Celui-ci reposait sur `midea-beautiful-air` dans un container `docker2` et n'a jamais été stable.
- Déclencheur : [fil community #151000](https://community.jeedom.com/t/log-container-please-try-again-5-minutes-later-pas-de-commandes-sur-mes-splits-midea/151000).
  - Erreurs rencontrées : `7610` (trop de tentatives de connexion, ban de 5 min à 24 h), `65027` (limite de connexions), `9999` (getToken NetHome Plus en panne), `3004` (getToken MSmartHome sans `applianceCodes`) et timeouts locaux.
  - Une fois token et key récupérés, l'appareil passait en ligne, mais aucune commande n'était créée.
- Référence fonctionnelle : [mill1000/midea-ac-py](https://github.com/mill1000/midea-ac-py), l'intégration Home Assistant basée sur `msmart-ng`.

## 2. Décisions validées

| Sujet | Décision |
|---|---|
| ID plugin | `mideamsmart`. `midea-msmart` est impossible car l'ID sert de nom de classe PHP. Nom affiché : **Midea MSmart** |
| Dossier | `/home/damien/kDrive/dev/2026/jeedom/mideamsmart` (renommé depuis `midea-msmart`) |
| Compte | Mono-compte **MSmartHome** saisi dans la configuration générale du plugin |
| Cloud | MSmartHome uniquement : NetHome Plus est cassé (9999). L'appareil doit être **appairé directement** sur ce compte, un partage ne suffit pas |
| Libs Python | **Hybride** : `msmart-ng` pour AC (0xAC) et CC (0xCC) ; `midea-local` pour A1 (déshumidificateur), pour le cloud (login, liste des appareils, token/key) et pour la découverte LAN de tous les types |
| Python | **venv** obligatoire, créé avec **uv 0.12.21** et un **CPython 3.13.15** autonome (`resources/python_runtime`), venv dans `resources/python_venv` |
| Découverte | **Cloud + LAN** : liste du compte, puis broadcast UDP pour l'IP, puis token/key récupérés **une seule fois** et stockés. Ensuite, contrôle 100 % local |
| Secours | Saisie manuelle de l'IP, du port, du token et de la key dans l'équipement |
| Compatibilité | `require` 4.5, Debian min 12 / max 13.99 |
| Catégorie | `energy` |
| Licence | Jeedom n'impose pas de licence aux plugins tiers, d'où **MIT**, cohérente avec msmart-ng et midea-local. À revérifier au moment de la publication sur le Market |
| Auteur | `Damien` provisoire dans info.json, **à confirmer** (pseudo Market) |
| Icône | Générée à partir de `template_icon.png` (PNG 309×348), avec une couleur distincte des plugins officiels |
| Git | Dépôt local, un commit par étape, sans remote pour l'instant |
| Tests | Aucun appareil disponible : tests unitaires et simulateur, puis testeurs du forum. Les captures d'écran de la doc seront fournies par Damien ; je prépare les emplacements |

## 3. Bibliothèques (versions épinglées)

| Lib | Version | Rôle | Remarques |
|---|---|---|---|
| `msmart-ng` | 2026.9.0 | Pilotage AC/CC (async, polling) | Python ≥3.10. Requiert ≥2026.8.1 pour `applianceCodes`. `Discover` force NetHome Plus, donc à utiliser avec `auto_connect=False` et en fournissant token/key nous-mêmes |
| `midea-local` | 12.3.0 | Cloud MSmartHome, découverte LAN, pilotage A1 | Python ≥3.12. Appareils sous forme de `Thread` avec push via `register_update`. `SmartHomeCloud.list_appliances()` et `get_cloud_keys(appliance_id)` |

API clés :

- **msmart-ng**
  - `AirConditioner(ip, port, device_id)` / `CommercialAirConditioner`
  - `authenticate(token, key)`, `get_capabilities()`, `refresh()`, puis propriétés + `apply()`
  - `to_dict()` et `capabilities_dict()`
  - Indicateurs `supports_*` pour savoir quelles commandes créer
- **midea-local**
  - `midealocal.cloud.SmartHomeCloud` : `login()`, `list_appliances()`, `get_cloud_keys()`
  - `midealocal.discover`
  - `midealocal.devices.device_selector(...)` puis `open()`, `register_update(cb)`, `set_attribute(attr, value)`, `refresh_status()`

Maintenir les versions épinglées dans `resources/requirements.in`, puis régénérer `resources/requirements.lock`. Avant chaque montée de version, consulter les changelogs et les issues ouvertes, en particulier [midea-ac-py#482](https://github.com/mill1000/midea-ac-py/issues/482).

## 4. Architecture

```
Jeedom PHP  ──socket TCP (apikey)──▶  démon Python (asyncio, venv 3.13)
            ◀──HTTP callback jeemideamsmart.php (apikey)──
                                     ├─ CloudService  (midea-local SmartHomeCloud)
                                     ├─ DiscoveryService (midea-local discover, UDP 6445)
                                     └─ drivers : AcDriver (msmart-ng), CcDriver (msmart-ng), A1Driver (midea-local)
```

- **Interface commune `BaseDriver`** (Python) : `connect()`, `refresh()`, `apply(changes)`, `get_state() -> dict`, `get_capabilities() -> dict`, `close()`.
- **AC/CC** : polling à intervalle configurable par équipement (30 s par défaut). L'état est envoyé à Jeedom **uniquement si une valeur change**, avec un envoi complet forcé toutes les N minutes.
- **A1** : push natif de midea-local. Le callback du thread est relayé vers la boucle asyncio via `loop.call_soon_threadsafe`.
- **Protection contre le ban cloud** :
  - Aucune connexion au cloud au démarrage du démon.
  - Connexion seulement sur action utilisateur (« Synchroniser ») ou quand le token/key manque.
  - Une seule session réutilisée, backoff exponentiel, arrêt immédiat sur les codes 7610 et 65027 avec un message clair.
- Le démon reçoit au démarrage, via socket, la liste des équipements actifs (id, type, ip, port, protocole, token, key, options). Il est notifié lors de toute sauvegarde ou suppression d'équipement.
- Gestion **hors ligne** : commande info `online` et backoff de reconnexion par appareil.

### Synchronisation — implémentée à l'étape 4

- **Déclenchement**, toujours asynchrone :
  - le bouton « Synchroniser » appelle l'ajax `syncDevices` ;
  - le bouton « Récupérer token/key depuis le cloud » de l'équipement appelle l'ajax `fetchDeviceKeys` ;
  - les deux passent par `mideamsmart::syncDevices($eqLogic = null)`, qui envoie au démon `syncDevices {account, password, broadcastAddress, knownDevices: {deviceId: {hasKeys, ipAddress, port}}, onlyDeviceId?, forceKeys?}`.
  - Les identifiants transitent uniquement par le socket local, jamais en ligne de commande.
- **Démon** (`sync.py` `SyncService`, avec dépendances injectables pour les tests) :
  1. Découverte LAN (`discovery.py`) : `midealocal.discover.discover(ip_address=…)` est synchrone, avec un timeout de 5 s, donc lancé via `asyncio.to_thread` en parallèle sur chaque adresse. Une liste vide signifie toutes les interfaces privées (`enum_all_broadcast`). Avec `onlyDeviceId`, la requête part en unicast vers l'IP connue.
  2. Cloud, si un compte est configuré (`cloud.py`) :
     - `CloudSession` (aiohttp + `midealocal.cloud.get_midea_cloud('SmartHome')`) : `login`, `list_appliances(None)`, `get_cloud_keys(id)`. La seconde renvoie deux couples (udpid méthodes 1 et 2).
     - L'**ID cloud** de l'appareil est l'ID LAN, ce qui sert de clé de fusion.
  3. Clés, seulement pour les types supportés en V3 dont les clés sont inconnues (ou forcées) :
     - chaque couple est essayé via `msmart.lan.LAN.authenticate`, qui fait le handshake 8370 indépendamment du type ;
     - seul un couple **accepté par l'appareil** est renvoyé.
  - `keysStatus` : `notNeeded`, `known`, `valid`, `invalid`, `unreachable`, `notOwned` (3201), `notInCloud`, `notOnLan`, `noAccount`, `cloudError`, `unsupported`.
  - Progression : `syncProgress {step: discovery|cloudLogin|cloudDevices|keys}`, puis `syncResult {devices, cloudError: {reason, cloudCode, retryAfter}|null, onlyDeviceId}` ou `{failed: alreadyRunning|internalError}`. Une seule synchro à la fois (`asyncio.Lock`).
- **Anti-ban** (`CloudGuard`, en mémoire du démon) :
  - 30 s minimum entre deux logins ;
  - après `7610`, blocage de 15 min ; après `65027`, 60 min ;
  - après `3101`/`3102`, refus tant que les identifiants ne changent pas.
  - Aucun login au démarrage du démon.
- **PHP** (`applySyncResult`) :
  - Les types non supportés sont ignorés et comptés.
  - Création d'un équipement : nom cloud, ou « Midea <type> » ; suffixe `<id>` si le nom est déjà pris sans objet ; catégorie `heating`.
  - `updateFromSync()` n'écrase **jamais** avec une valeur vide et ne renomme pas. Les clés ne sont écrites que si elles sont fournies (donc validées).
  - Messages traduits via `event::add('jeedom::alert', {page: 'mideamsmart'})`. Les noms sont échappés (`htmlspecialchars`), car les messages acceptent du HTML.
  - `event::add('mideamsmart::syncDone', {created, message, level})`. Le JS écoute en DOM **et** en jQuery, car le core déclenche les événements non-core via jQuery quand il est chargé. Il recharge la page seulement si des équipements ont été créés, et réaffiche alors le résumé via `sessionStorage`.
- **Adresse de diffusion** : vide par défaut, c'est-à-dire automatique (`DEFAULT_BROADCAST_ADDRESS = ''`).
- **Testé** :
  - 22 tests unitaires : guard, session cloud factice, scénarios de synchro complète, sans compte, cloud bloqué, appareil unique ;
  - appels réels à la découverte (0 appareil) et à `check_keys` (port fermé → `unreachable`) ;
  - sur l'instance de dev Jeedom 4.6.1 :
    - synchro sans compte de bout en bout ;
    - faux `syncResult` posté sur le vrai callback : création, mise à jour, clés chiffrées en base, alertes ;
    - UI dans le navigateur : bouton Synchroniser, rechargement et résumé, bouton des clés sans compte → message clair.
  - **Non testé** avec un vrai compte MSmartHome ni avec de vrais appareils : à valider par des testeurs.

### Démon — implémenté à l'étape 3

- Code dans `resources/mideamsmartd/` : `mideamsmartd.py` (entrée, argparse) et le paquet `mideamsmart_daemon/`.
  - `jeedom.py` : `JeedomSocketServer`, `JeedomCallback`, `setup_logging`, `redact`.
  - `devices.py` : `DeviceConfig` (token et key en `repr=False`), `DeviceManager`.
  - `daemon.py` : `Daemon` (cycle de vie, table `_handlers` action → coroutine).
  - Tests `unittest` dans `tests/`. Lancement : `cd resources/mideamsmartd && <venv>/bin/python3 -m unittest discover -s tests -t .` (aiohttp, présent dans le venv, sert de faux Jeedom).
- Arguments : `--loglevel --sockethost(127.0.0.1) --socketport --callback --apikey --pid --cycle(0.5)`. Le PID est dans `jeedom::getTmpFolder('mideamsmart')/deamon.pid`, et la sortie part dans le log `mideamsmart_daemon`.
- **Jeedom → démon** (`mideamsmart::sendToDaemon`) : `stream_socket_client` vers `127.0.0.1:port`, **une ligne JSON par connexion**, avec `apikey` (comparée via `hmac.compare_digest`) et `action`. Taille max 1 Mo, timeout de lecture 10 s. Chaque handler tourne dans sa propre tâche, pour ne jamais bloquer le socket.
  - Actions : `setDevices {devices: [...]}`, `updateDevice {device}`, `removeDevice {eqLogicId}`, `stop`.
- **Démon → Jeedom** (`JeedomCallback`, httpx) : POST JSON sur `core/php/jeemideamsmart.php?apikey=…`, 3 essais. Le test de démarrage (`GET …&test=1`) attend `OK`, sinon exit 1.
  - Messages : `daemonStarted {pid}`, auquel PHP répond par `setDevices` ; `deviceValues {devices: {eqLogicId: {logicalId: valeur}}}`, fusionnés et envoyés tous les `cycle` s, puis appliqués via `checkAndUpdateCmd`.
  - Dispatch PHP dans `mideamsmart::handleDaemonMessage()`.
- Config envoyée par équipement : `mideamsmart::getDaemonConfig()`, avec les clés `eqLogicId, deviceId(logicalId), deviceType, name, ipAddress, port, protocolVersion, token, key, pollingInterval`.
  - `postSave` envoie `updateDevice`, ou `removeDevice` si l'équipement est désactivé ; `preRemove` envoie `removeDevice`.
  - `postConfig_defaultPollingInterval` renvoie toute la liste.
- Arrêt :
  - `deamon_stop` : SIGTERM sur le PID, attente de 5 s, puis `system::kill('mideamsmartd.py')` en dernier recours. Pas de `fuserk` sur le port, pour ne pas tuer un autre processus.
  - Côté démon : SIGTERM/SIGINT provoquent la fermeture du socket, le flush du callback et la suppression du PID.
- **Logs** : jamais de secret.
  - Les messages sont passés par `redact` (apikey, token, key, password, cloudAccount, cloudPassword).
  - Les loggers `httpx` et `httpcore` sont forcés à WARNING, car ils écrivent l'URL contenant l'apikey.
  - `msmart` et `midealocal` ne sont verbeux qu'en debug.
- **Testé** :
  - 11 tests unitaires et de bout en bout ;
  - processus réel lancé en CLI puis arrêté par SIGTERM ;
  - classe PHP réelle (avec un faux core minimal, en PHP 8.2) envoyant 143 Ko au démon réel.
  - **Non testé** dans une vraie instance Jeedom (`deamon_start`, callback HTTP via Apache).

## 5. Arborescence et nommage (conventions du core)

PHP et JS en camelCase, classes en PascalCase. Python en PEP8 (`snake_case`, classes en `PascalCase`). Tous les identifiants sont en anglais.

```
mideamsmart/
├── plugin_info/  info.json, install.php, configuration.php, mideamsmart_icon.png  (pas de packages.json : dépendances procédurales)
├── core/class/   mideamsmart.class.php   (class mideamsmart extends eqLogic, class mideamsmartCmd extends cmd)
├── core/ajax/    mideamsmart.ajax.php
├── core/php/     jeemideamsmart.php       (callback du démon)
├── core/config/  commands/*.json          (définitions des commandes par type)
├── core/i18n/    en_US.json es_ES.json it_IT.json ru_RU.json pt_PT.json de_DE.json
├── desktop/php/  mideamsmart.php
├── desktop/js/   mideamsmart.js
├── desktop/modal/ (diagnostic d'un appareil : état brut + capacités)
├── resources/    install_apt.sh, requirements.in, requirements.lock, mideamsmartd/ (mideamsmartd.py, jeedom/, drivers/, services/)
│               (générés, ignorés par git : python_runtime/, python_venv/)
├── docs/<lang>/  index.md, changelog.md  (fr_FR + 6 langues), docs/images/
└── PROJECT.md    (ce fichier)
```

- Logs : `mideamsmart` (PHP), `mideamsmart_daemon` et `mideamsmart_update` (dépendances, convention des plugins officiels).
- **Dépendances** (méthode procédurale, pas de `packages.json`) — implémenté et testé à l'étape 2 :
  - `dependancy_install()` renvoie `resources/install_#stype#.sh <progress_file>`, avec `#stype#` = `apt` et le fichier de progression dans `jeedom::getTmpFolder('mideamsmart')/dependance`. Le core l'exécute en **root** (sudo / at).
  - `resources/install_apt.sh` :
    - détecte l'architecture via `dpkg --print-architecture` (amd64, arm64, armhf), pas `uname -m`, car un Pi peut avoir un noyau 64 bits et un système 32 bits ;
    - installe si besoin `ca-certificates`, `curl`, et `build-essential` **sur armhf seulement** (pycryptodome n'a pas de wheel armv7, il est compilé) ;
    - télécharge uv dans un dossier temporaire, avec vérification SHA-256 par architecture (sommes en dur dans le script) ;
    - `UV_PYTHON_INSTALL_DIR=resources/python_runtime`, `UV_CACHE_DIR` temporaire, `UV_NO_CONFIG=1`, `UV_LINK_MODE=copy` ;
    - lance `uv python install --no-bin 3.13.15`, recrée le venv (`--managed-python`), puis `uv pip sync --require-hashes resources/requirements.lock` ;
    - vérifie l'import de `msmart` et `midealocal`, puis supprime les **anciennes** versions de Python de `python_runtime` uniquement (jamais le Python système) ;
    - écrit le marqueur `python_venv/.mideamsmart_dependencies` = sha256(install_apt.sh + requirements.lock) et fait un `chown -R www-data`.
  - `dependancy_info()` renvoie `ok` si `python_venv/bin/python3` est exécutable **et** que le marqueur correspond à l'empreinte recalculée en PHP. Une mise à jour du script ou du lock repasse donc les dépendances en NOK.
  - `backupExclude()` exclut `resources/python_runtime` (le core exclut déjà `python_venv`). Le venv survit aux mises à jour du plugin, car le core ne vide pas le dossier.
  - Taille : environ 106 Mo (runtime) + 25 Mo (venv).
  - **Testé** dans des conteneurs `debian:12-slim` et `debian:13-slim` en **amd64** : installation, réinstallation, montée 3.13.14 → 3.13.15, Python système intact, import en `www-data`, empreinte PHP = marqueur.
  - **Non testé** sur arm64 et armhf : pas d'émulation qemu disponible sur le poste de dev. À valider par des testeurs Raspberry Pi.
- **Versions Python** : `resources/requirements.in` contient les deps directes ; `resources/requirements.lock` est universel et hashé, généré par `tools/lock_requirements.sh <uv>`. Pour monter de version :
  - modifier `requirements.in` et/ou `UV_VERSION` + `UV_SHA256` / `PYTHON_VERSION` dans `install_apt.sh` (uv ≥ 2 semaines) ;
  - relancer le lock et retester dans Docker.
- Démon lancé avec `resources/python_venv/bin/python3`. Port configurable, **55114** par défaut (`mideamsmart::DEFAULT_SOCKET_PORT`).

**Règles de code** (vérifiées à l'étape 1) :
- PHP compatible **7.4, 8.0 et 8.2** : le workflow `jeedom/workflows` lint ces trois versions. Pas de `match`, ni de `?->`, ni d'arguments nommés, ni de `str_contains` côté PHP.
- JS en **vanilla core 4.4+**, sans jQuery : `domUtils.ajax`, `jeedomUtils.showAlert`, `setJeeValues`, `jeeFrontEnd.mideamsmart`. Le tri du tableau des commandes est géré par le core.
- Textes : `{{…}}` en PHP/JS, `__('…', __FILE__)` en PHP, en français. Logs utilisateur traduits.
- Lint local : `docker run --rm -v "$PWD":/app:ro -w /app php:7.4-cli …` (idem 8.2), `node --check` via `node:22-alpine`.

**Outils de dev** (`tools/`, non utilisés par Jeedom) :
- `tools/i18n.py check|update [traductions.json]` : extrait les chaînes et met à jour `core/i18n/*.json` (fichier source → chaîne FR → traduction).
- `tools/lock_requirements.sh [uv]` : régénère `resources/requirements.lock`.
- `tools/make_icons.py <template_icon.png>` : génère `plugin_info/mideamsmart_icon.png` (forme reprise du modèle Jeedom, dégradé bleu `#0E4A8C` → `#20A0DC`) et `desktop/img/{ac,cc,a1}.png`.

## 6. Configuration

**Plugin (générale)** :
- Email et mot de passe MSmartHome. Un avertissement recommande un compte dédié et rappelle que l'appareil doit être appairé directement sur ce compte.
- Port du démon.
- Adresse(s) de broadcast pour la découverte (par défaut `255.255.255.255`).
- Intervalle de polling par défaut.
- Clés de config : `cloudAccount` et `cloudPassword` (chiffrées via `$_encryptConfigKey`), `broadcastAddress`, `defaultPollingInterval`, `socketport`.

**Page du plugin** : bouton **« Synchroniser »** (`#bt_mideamsmartSyncDevices`, action ajax `syncDevices`), « Ajouter » (création manuelle) et « Configuration ».

**Équipement** (`logicalId` = ID appareil Midea). Clés de configuration : `deviceType` (AC/CC/A1), `ipAddress`, `port`, `protocolVersion`, `token` et `key` (chiffrées via `encrypt()`/`decrypt()`), `pollingInterval`, `serialNumber`, `model`.
- Champs **lecture seule** : type (AC/CC/A1…), SN, modèle.
- Connexion : IP, port (6444), version de protocole (2/3), token et key (champs masqués, éditables).
- Actions :
  - bouton « Récupérer token/key » ;
  - bouton « Recréer les commandes » (selon les capacités).
- Options :
  - polling (s), pas de consigne (0,5 / 1), bip des commandes ;
  - format énergie (BCD/binaire) et échelle ;
  - activation des données de diagnostic (groupes 1/2/7/11).

## 7. Commandes

### Principe — implémenté à l'étape 5 (AC/CC)

- **Définitions** : `core/config/commands.json`.
  - `enums` donne les libellés traduits (`{{…}}`) par famille de valeurs.
  - `commands` liste les commandes, avec les champs `logicalId, name, type, subType, types[AC|CC|A1], feature?, genericType?, unit?, isVisible?, isHistorized?, value? (logicalId de l'info liée), listEnum?, minValue/maxValue?, minFrom/maxFrom/stepFrom? (clés des capacités), step?, icon?, template?`.
  - Le fichier est chargé via `translate::exec(…, 'plugins/mideamsmart/core/config/commands.json')`. **Pas de guillemets doubles** dans les traductions, puisqu'elles sont injectées dans du JSON.
- **Capacités** : le démon envoie `deviceCapabilities {eqLogicId, deviceType, capabilities: {complete, minTargetTemperature, maxTargetTemperature, temperatureStep, features[], enums{famille: [codes supportés]}}}` à la première réponse de l'appareil, puis à chaque changement.
  - PHP `applyCapabilities()` les stocke dans la configuration `capabilities`, avec un `save(true)` direct (pas de `postSave`), puis appelle `createCommands(false)`.
  - `createCommands($removeObsolete)` traite d'abord les infos, puis les actions, pour pouvoir les lier. Il crée les manquantes et met à jour `listValue`, min, max, `step` et la liaison `value`. Il ne modifie **jamais** le nom, la visibilité ni l'historique des commandes existantes.
  - Le core retire les apostrophes ASCII des noms (`cleanComponanteName`) : on les remplace par `’` à la création.
  - Après une création, PHP envoie `resendValues`, car le démon ne pousse que les valeurs qui changent.
  - Le bouton « Mettre à jour les commandes » appelle l'ajax `updateCommands`, qui fait `createCommands(true)` puis envoie `refreshCapabilities` au démon.
- **Valeurs** :
  - les infos texte portent un **code stable** (`cool`, `fan_only`, `eco`…, c'est-à-dire le nom d'enum msmart en minuscules) ;
  - les actions `select` affichent les libellés traduits ;
  - les booléens valent 0 ou 1 ;
  - les infos doublées par une action liée sont masquées par défaut.
- **Exécution** : `mideamsmartCmd::execute` envoie `executeCommand {eqLogicId, command: logicalId, value}`, avec la valeur `slider` ou `select`.
  - Le driver valide la valeur contre l'enum et les valeurs supportées, applique la commande, puis relit l'état.
  - En cas d'erreur, il renvoie `commandError {reason: unknownCommand|invalidValue|unsupportedValue|deviceOffline|communicationError|deviceNotRunning}`, que PHP écrit en warning traduit.
- **Préréglages** : une **liste exclusive** `preset`/`setPreset`, comme dans midea-ac-py, à la place d'interrupteurs séparés.
  - AC : `none, sleep, freeze_protection, eco, ieco, turbo` ;
  - CC : `none, eco, silent, sleep`.
- **Options d'équipement** : `beep` (1 par défaut), `temperatureStep` (1 ou 0,5), `energy` (0), `energyFormat` (`bcd` ou `binary`), `energyScale` (1). Elles sont envoyées dans `getDaemonConfig`. `preSave` force des valeurs explicites pour que les cases à cocher de la page restent justes.

### Démon — drivers (`mideamsmart_daemon/drivers/`)

- **`BaseDriver`** :
  - boucle de polling par appareil, avec un `asyncio.Lock` partagé avec les commandes ;
  - `online` publié à chaque transition ;
  - **backoff** quand l'appareil ne répond pas : l'intervalle double jusqu'à 300 s ;
  - publication des seules valeurs changées, plus un renvoi complet toutes les 10 min ;
  - `request_refresh`, `resend_values`, `resend_capabilities`.
- **`MsmartDriver`** :
  - instancie `AirConditioner` ou `CommercialAirConditioner` ;
  - fait `authenticate(token, key)` en V3 ;
  - appelle `get_capabilities()`. Comme msmart ne renvoie aucun résultat, le succès est détecté en enveloppant `_update_capabilities`. Sans réponse, les capacités par défaut sont utilisées (`complete: false`) et la demande est refaite toutes les 10 min.
  - Avant chaque commande : `fahrenheit=False` ; `sound` n'est écrit que si `supports_sound`. Sinon, on écrit `_sound` directement, car le setter `sound` provoque **toujours** une commande SetProperties SOUND, que les appareils sans cette capacité n'acquittent pas (6 s de timeout constatées avec le faux appareil).
  - `execute` lève `deviceOffline` si l'appareil ne répond plus après la commande, car msmart ne lève pas d'erreur dans ce cas.
- **`AcDriver` / `CcDriver`** : `read_capabilities()` (features + enums), `read_values()`, `command_handlers()`.
  - Choisir un mode met l'appareil en marche.
  - La consigne est bornée aux limites de l'appareil et arrondie à 0,5.
- `DeviceManager` démarre ou arrête le driver de chaque équipement (registre `DRIVERS = {AC, CC}`). A1 vient à l'étape 6.

### Tests de l'étape 5

- `tests/test_drivers.py` : faux appareils qui héritent des **vraies** classes msmart-ng (seuls les appels réseau sont remplacés, capacités via `override_capabilities`).
- **`tools/fake_ac.py`** : faux climatiseur LAN **V2** qui répond avec les trames réelles des tests msmart-ng (capacités 0xB5, état 0xC0) et applique alimentation, mode, consigne et ventilation des SetState.
  - Dans l'instance de dev : `docker exec -d jeedom-dev sh -c 'cd /var/www/html/plugins/mideamsmart && exec resources/python_venv/bin/python3 tools/fake_device.py --type ac --port 6444 > /tmp/fake_ac.log 2>&1'` (idem `--type a1 --port 6445`), puis équipements « Clim test » (127.0.0.1:6444) et « Déshumidificateur test » (127.0.0.1:6445), en V2. Il faut les relancer après un redémarrage du conteneur. Pour les arrêter : `docker exec jeedom-dev pkill -f "^resources/python_venv/bin/python3 tools/fake"`.
  - **Validé de bout en bout** : capacités lues via le vrai protocole, 19 commandes créées, valeurs remontées, `setMode`, `setTargetTemperature`, `on`, `off` et `setFanSpeed` appliqués, `ieco` refusé (`unsupportedValue`), widget du dashboard correct.
- **Non testé** : appareils réels, protocole V3 (handshake), appareils CC réels, consommation électrique.

### A1 déshumidificateur — implémenté à l'étape 6 (midea-local)

- **`A1Driver`** (`drivers/a1.py`) : adaptateur du **thread** midea-local (`MideaA1Device`, créé via `device_selector`) vers asyncio.
  - Le thread gère la connexion, la reconnexion (backoff de 5 à 600 s), la requête périodique (`set_refresh_interval` = intervalle de l'équipement) et le heartbeat.
  - `register_update` est relayé dans la boucle par `call_soon_threadsafe`. Les mises à jour sont traitées une par une (`_update_lock`) ; `available` donne la commande `online`.
  - Les commandes passent par `set_attribute` dans `asyncio.to_thread` : l'appel est bloquant et l'appareil répond avec son nouvel état. **Choisir un mode** sur un appareil éteint envoie la mise en marche, **attend sa confirmation** (10 s maximum), puis envoie le mode. Sans cette attente, le message de mode, construit depuis les attributs connus, ferait repasser l'appareil à l'arrêt.
  - `request_refresh` remet `_previous_refresh` à 0 : seul le thread doit écrire les requêtes sur le socket.
  - `prompt_tone` est réglé selon l'option bip. Le pas de consigne est masqué pour A1.
  - Capacités : `features` = `targetHumidity, swing, childLock, anion, waterLevelSet`, plus `pump` si le bit `pump_enable` est présent. `enums` = `mode` (`device.modes`), `fanSpeed` (sauf `off`), `waterLevelSet`. Consigne d'humidité de 35 à 85 %.
- **Commandes A1** (dans `commands.json`, `types: ["A1"]`) :
  - communes : `refresh, online, power/on/off, fanSpeed/setFanSpeed, targetHumidity/setTargetHumidity` (min et max via `minTargetHumidity`/`maxTargetHumidity`) ;
  - `mode/setMode` sans type générique thermostat ;
  - `currentHumidity` (HUMIDITY), `currentTemperature` (TEMPERATURE), `tankLevel`, `tankFull`, `waterLevelSet/setWaterLevelSet` ;
  - `swing`, `childLock`, `anion`, `pump` avec `…On`/`…Off` ;
  - `filterCleaningReminder`, `resetFilter`.
- **Alertes binaires** (`tankFull`, `filterCleaningReminder`, `filterAlert`) : template `core::tmplicon` avec `displayParameters` `_icon_on_` (rouge) et `_icon_off_` (vert). Le HTML des icônes doit être en **guillemets simples**, car le template l'injecte dans une chaîne JS entre guillemets doubles.
- **Concurrence** : `_capabilities_sent` est mis à jour **avant** l'envoi, sinon deux mises à jour simultanées créaient les commandes deux fois (erreur MySQL « Duplicate entry »).
- **`tools/fake_device.py --type ac|a1`** remplace `fake_ac.py`. Le faux A1 répond aux requêtes appliance (0xA0), query (0x41) et set (0x48) avec la disposition des réponses midea-local.
- **Testé** :
  - `tests/test_integration.py` : drivers AC et A1 avec les **vraies** libs contre les faux appareils (état, commandes, appareil hors ligne) ; 32 tests au total.
  - Instance de dev : équipement « Déshumidificateur test » (127.0.0.1:6445, V2) créé avec 31 commandes, commandes `off`, `setMode` (avec remise en marche), `setTargetHumidity`, `setFanSpeed` appliquées, widget vérifié.
  - **Non testé** : vrai déshumidificateur, protocole V3, nouveau protocole A1 (B0/B1, lumière).

## 8. Traductions et documentation

- Langues : **fr_FR** (source), en_US, es_ES, it_IT, ru_RU, pt_PT, de_DE.
- Textes PHP et JS en `{{…}}`, fichiers `core/i18n/*.json`, `description` de `info.json` traduite.
- Docs `docs/<lang>/index.md` et `changelog.md`, avec captures dans `docs/images/`.
  - Emplacements prévus : configuration du plugin, synchronisation, page équipement, commandes AC, commandes A1, modal diagnostic.
- Mettre à jour la doc et le changelog à chaque évolution visible.

## 9. Points ouverts / à faire

- [ ] Auteur (pseudo Market) dans `info.json` et `LICENSE`.
- [ ] URL du dépôt GitHub : remplacer `OWNER` dans les liens documentation/changelog de `info.json`.
- [ ] Captures d'écran à fournir dans `docs/images/` : `plugin_config.png` (configuration du plugin), `plugin_devices.png` (page du plugin), `device_config.png` (onglet Équipement). À compléter plus tard : commandes AC, commandes A1, modal diagnostic.
- [ ] Tester l'installation des dépendances sur Raspberry Pi arm64 et armhf.
- [x] Tester le cycle de vie du démon dans une vraie instance Jeedom (instance Docker de dev `../dev-env`, voir son README).
- [ ] Valider la synchronisation et le pilotage avec un vrai compte MSmartHome et de vrais appareils V2/V3, AC et CC (testeurs du forum).
- [ ] Options avancées non exposées (étape 7 ou plus tard) : données de diagnostic groupes 1/2/7/11, follow me, surcharge des capacités (`override_capabilities`).
- [ ] Dev en Docker bridge : la découverte LAN ne voit que le réseau du conteneur. Prévoir `network_mode: host` pour tester avec de vrais appareils.
- [ ] Vérifier, sur une vraie réponse cloud, l'appariement entre l'`appliance_id` du cloud et le `device_id` de la découverte LAN.
- [ ] Plan de tests sans matériel : tests unitaires des drivers avec appareils simulés et trames issues des tests des libs.

## 10. Étapes de réalisation (prévisionnel)

1. ✅ Squelette du plugin depuis plugin-template : info.json, icône, classes, page desktop, config, i18n (6 langues), docs (7 langues).
2. ✅ Dépendances : install via uv, venv, `dependancy_info` (testé amd64 Debian 12/13).
3. ✅ Démon : socket, callback, cycle de vie (services cloud et découverte déplacés à l'étape 4).
4. ✅ Synchronisation : services cloud (MSmartHome) et découverte LAN, création des équipements, récupération de token/key.
5. ✅ Driver AC/CC et création des commandes selon les capacités.
6. ✅ Driver A1.
7. Modal diagnostic, robustesse (hors ligne, backoff, anti-ban).
8. Traductions dans les 6 langues, documentation et changelog.
