# mideamsmart — Récapitulatif projet

> Document de référence du plugin, à relire avant chaque étape et à mettre à jour à chaque décision.
> Dernière mise à jour : 2026-10-16

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
| Python | **venv** obligatoire, créé avec **uv** et un **Python 3.13** autonome dans `resources/python_venv` |
| Découverte | **Cloud + LAN** : liste du compte, puis broadcast UDP pour l'IP, puis token/key récupérés **une seule fois** et stockés. Ensuite, contrôle 100 % local |
| Secours | Saisie manuelle de l'IP, du port, du token et de la key dans l'équipement |
| Compatibilité | `require` 4.5, Debian min 12 / max 13.99 |
| Catégorie | `energy` |
| Licence | Jeedom n'impose pas de licence aux plugins tiers, d'où **MIT**, cohérente avec msmart-ng et midea-local. À revérifier au moment de la publication sur le Market |
| Auteur | **À confirmer** (pseudo Market) |
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

Maintenir les versions épinglées dans `resources/requirements.txt`. Avant chaque montée de version, consulter les changelogs et les issues ouvertes, en particulier [midea-ac-py#482](https://github.com/mill1000/midea-ac-py/issues/482).

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
├── resources/    install_apt.sh, requirements.txt, mideamsmartd/ (mideamsmartd.py, jeedom/, drivers/, services/)
├── docs/<lang>/  index.md, changelog.md  (fr_FR + 6 langues), docs/images/
└── PROJECT.md    (ce fichier)
```

- Logs : `mideamsmart` (PHP) et `mideamsmart_daemon`. Le log des dépendances suit la convention du core (à vérifier).
- Dépendances : `dependancy_install()` lance `resources/install_apt.sh`, qui :
  - télécharge un binaire **uv épinglé**, avec vérification de la somme SHA-256 ;
  - installe Python 3.13 en fixant `UV_PYTHON_INSTALL_DIR` dans le plugin ;
  - lance `uv venv resources/python_venv`, puis `uv pip install -r requirements.txt`.
  - Architectures visées : x86_64, aarch64 et armv7.
- `dependancy_info()` vérifie le binaire Python du venv **et** les versions des libs.
- Démon lancé avec `resources/python_venv/bin/python3`. Le port est configurable, valeur par défaut à choisir (libre, ≠ 55009).

## 6. Configuration

**Plugin (générale)** :
- Email et mot de passe MSmartHome. Un avertissement recommande un compte dédié et rappelle que l'appareil doit être appairé directement sur ce compte.
- Port du démon.
- Adresse(s) de broadcast pour la découverte (par défaut `255.255.255.255`).
- Intervalle de polling par défaut.
- Bouton **« Synchroniser les appareils »**.

**Équipement** (`logicalId` = ID appareil Midea) :
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

Les commandes sont créées **selon les capacités** remontées par l'appareil (`get_capabilities` / `supports_*`) et recréables à la demande. Les valeurs suivent `/dev/fr_FR/cmd_value` et les types génériques du core 4.5+.

### Communes
| logicalId | Type | Générique |
|---|---|---|
| `online` | info binary | — |
| `refresh` | action other | — |

### AC (0xAC) et CC (0xCC) — msmart-ng
| Info | Action(s) | Générique | Condition |
|---|---|---|---|
| `power` (binary) | `on`, `off` | ENERGY_STATE / ENERGY_ON / ENERGY_OFF | toujours |
| `mode` (string : auto, cool, dry, heat, fan_only, smart_dry) | `setMode` (select) | THERMOSTAT_MODE / THERMOSTAT_SET_MODE | `supported_operation_modes` |
| `targetTemperature` (°C) | `setTargetTemperature` (slider min/max) | THERMOSTAT_SETPOINT / THERMOSTAT_SET_SETPOINT | toujours |
| `indoorTemperature` | — | THERMOSTAT_TEMPERATURE | toujours |
| `outdoorTemperature` | — | THERMOSTAT_TEMPERATURE_OUTDOOR | si valeur remontée |
| `fanSpeed` | `setFanSpeed` (select ou slider si vitesse custom) | FAN_SPEED_STATE / FAN_SPEED | `supported_fan_speeds` |
| `swingMode` | `setSwingMode` (select) | — | `supported_swing_modes` |
| `horizontalSwingAngle`, `verticalSwingAngle` | `setHorizontalSwingAngle`, `setVerticalSwingAngle` | — | `supports_*_swing_angle` |
| `indoorHumidity` | — | THERMOSTAT_HUMIDITY | `supports_humidity` |
| `targetHumidity` | `setTargetHumidity` | HUMIDITY_SETPOINT / HUMIDITY_SET_SETPOINT | `supports_target_humidity` |
| `eco`, `ieco`, `turbo`, `flash`, `sleep`, `followMe`, `freezeProtection`, `purifier`, `outSilent` | `xxxOn` / `xxxOff` | — | `supports_*` |
| `breezeMode` (off, breeze_away, breeze_mild, breezeless) | `setBreezeMode` | — | `supports_breeze*` |
| `displayOn` | `toggleDisplay` | — | `supports_display_control` |
| `auxMode`, `rateSelect`, `cascadeMode`, `freshAirFanSpeed` | `setAuxMode`, `setRateSelect`, `setCascadeMode`, `setFreshAirFanSpeed` | — | listes supportées |
| `selfCleanActive` | `startSelfClean` | — | `supports_self_clean` |
| `filterAlert`, `defrostActive`, `errorCode` | — | — | toujours / si remonté |
| `realTimePower` (W), `totalEnergy` (kWh), `currentEnergy` (kWh) | — | POWER / CONSUMPTION | option énergie activée |
| diagnostics : `compressorFrequency`, `compressorCurrent`, `outdoorFanSpeed`, `indoorCoilTemperature`… | — | — | option diagnostic |

Sur le CC, les noms sont alignés sur ceux de l'AC quand l'équivalent existe : `silent`, `purifier` (select), `display`.

### A1 déshumidificateur — midea-local
| Info | Action(s) | Générique |
|---|---|---|
| `power` | `on`, `off` | ENERGY_* |
| `mode` (manual, continuous, auto, clothes_dry, shoes_dry, silent) | `setMode` | — |
| `fanSpeed` | `setFanSpeed` | FAN_SPEED_STATE / FAN_SPEED |
| `targetHumidity` | `setTargetHumidity` | HUMIDITY_SETPOINT / HUMIDITY_SET_SETPOINT |
| `currentHumidity` | — | HUMIDITY |
| `currentTemperature` | — | TEMPERATURE |
| `tankLevel` (%), `tankFull` | — | — |
| `swing`, `childLock`, `anion`, `pump` | `xxxOn` / `xxxOff` | — |
| `filterCleaningReminder` | — | — |

Les autres types listés par le cloud (FD, FA, B6…) sont affichés comme **« non supporté »**, sans création de commandes. L'architecture par drivers permet de les ajouter plus tard.

## 8. Traductions et documentation

- Langues : **fr_FR** (source), en_US, es_ES, it_IT, ru_RU, pt_PT, de_DE.
- Textes PHP et JS en `{{…}}`, fichiers `core/i18n/*.json`, `description` de `info.json` traduite.
- Docs `docs/<lang>/index.md` et `changelog.md`, avec captures dans `docs/images/`.
  - Emplacements prévus : configuration du plugin, synchronisation, page équipement, commandes AC, commandes A1, modal diagnostic.
- Mettre à jour la doc et le changelog à chaque évolution visible.

## 9. Points ouverts / à faire

- [ ] Auteur (pseudo Market) dans `info.json`.
- [ ] Choisir le port par défaut du démon (vérifier qu'il n'entre pas en conflit avec des plugins connus).
- [ ] Vérifier la compatibilité des dépendances msmart-ng ↔ midea-local dans un même venv (`httpx` / `aiohttp` / `pycryptodome`).
- [ ] Vérifier la convention de nom du log des dépendances et l'usage de `resources/python_venv` face au core 4.5.
- [ ] Vérifier, sur une vraie réponse cloud, l'appariement entre l'`appliance_id` du cloud et le `device_id` de la découverte LAN.
- [ ] Plan de tests sans matériel : tests unitaires des drivers avec appareils simulés et trames issues des tests des libs.

## 10. Étapes de réalisation (prévisionnel)

1. Squelette du plugin depuis plugin-template : info.json, icône, classes, page desktop, config, i18n vide.
2. Dépendances : install via uv, venv, `dependancy_info`.
3. Démon : socket, callback, cycle de vie, services cloud et découverte.
4. Synchronisation : création des équipements, récupération de token/key.
5. Driver AC/CC et création des commandes selon les capacités.
6. Driver A1.
7. Modal diagnostic, robustesse (hors ligne, backoff, anti-ban).
8. Traductions dans les 6 langues, documentation et changelog.
