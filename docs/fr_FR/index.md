# Plugin Midea MSmart

> **Plugin en cours de développement** : cette documentation décrit l'état actuel du plugin et sera complétée à chaque version.

## Présentation

Le plugin **Midea MSmart** permet de piloter **en local** les climatiseurs et déshumidificateurs Midea et des marques associées (Comfee, Inventor, Qlima…) compatibles avec l'application **MSmartHome**.

Le compte MSmartHome sert uniquement à :

- lister les appareils associés au compte ;
- récupérer une seule fois les clés d'authentification (*token* et *key*) des appareils récents (protocole V3).

Ensuite, toutes les commandes et lectures d'état passent directement par le réseau local, sans le cloud Midea.

Appareils pris en charge :

| Type | Appareil |
|---|---|
| `0xAC` | Climatiseur (split, mobile, PortaSplit…) |
| `0xCC` | Climatiseur commercial |
| `0xA1` | Déshumidificateur |

## Prérequis

- Jeedom 4.5 ou supérieur, sur Debian 12 ou 13.
- Les appareils et Jeedom doivent être sur le **même réseau local** (même sous-réseau), afin que la découverte fonctionne.
- Un compte **MSmartHome** sur lequel les appareils sont **appairés directement**. Un appareil seulement *partagé* depuis un autre compte ne permet pas de récupérer ses clés.

> **Conseil**
>
> Utilisez de préférence un mot de passe composé uniquement de lettres et de chiffres.
> Après plusieurs échecs de connexion, le cloud Midea bloque temporairement le compte, de quelques minutes à 24 heures (erreurs `7610` ou `65027`). Dans ce cas, attendez avant de réessayer.

## Configuration du plugin

Après l'installation, activez le plugin puis lancez l'installation des dépendances. Le plugin installe son propre environnement Python, isolé du système.

### Dépendances

L'installation des dépendances, lancée depuis la page de configuration du plugin, installe dans le dossier du plugin uniquement :

- **Python 3.13** autonome, téléchargé avec l'outil [uv](https://github.com/astral-sh/uv), indépendamment de la version de Python du système ;
- un environnement virtuel (`resources/python_venv`) contenant les bibliothèques du plugin, en versions figées et vérifiées par empreinte.

L'installation prend quelques minutes et occupe environ 130 Mo. Sur un système 32 bits (Raspberry Pi en `armhf`), un compilateur est aussi installé et l'opération est plus longue, car une bibliothèque doit y être compilée.

Après une mise à jour du plugin qui change ces versions, les dépendances repassent à l'état *NOK* : relancez simplement leur installation. Elles ne sont pas incluses dans les sauvegardes Jeedom ; après une restauration, relancez leur installation.

### Paramètres

![Configuration du plugin](../images/plugin_config.png)

- **Compte MSmartHome**
  - **Identifiant (email)** et **Mot de passe** du compte MSmartHome.
- **Réseau local**
  - **Adresse de diffusion** : adresse(s) de broadcast utilisée(s) pour découvrir les appareils, séparées par des virgules. Laissez vide (par défaut) pour diffuser sur toutes les interfaces réseau de Jeedom. Si les appareils ne sont pas trouvés, indiquez l'adresse de broadcast de leur réseau (par exemple `192.168.1.255`).
  - **Intervalle d'interrogation par défaut** : délai en secondes entre deux lectures de l'état des appareils (30 s par défaut, 10 s minimum).
- **Démon**
  - **Port du démon** : port local utilisé par le démon (55114 par défaut). Ne le modifiez qu'en cas de conflit avec un autre plugin.

### Démon

Le démon assure la communication locale avec les appareils. Une fois les dépendances installées, il démarre automatiquement (gestion automatique activée), ou se lance avec le bouton **(Re)Démarrer** de la page de configuration du plugin.

- Il n'écoute que sur la machine Jeedom (`127.0.0.1`), sur le port défini ci-dessus.
- Il ne se connecte **jamais** au cloud Midea à son démarrage, ce qui évite les blocages de compte.
- Ses messages sont dans le log `mideamsmart_daemon`, ceux de l'installation des dépendances dans `mideamsmart_update`. Passez le niveau de log du plugin en *Debug* pour obtenir le détail des échanges. Le plugin y masque les mots de passe, *token* et *key*.

## Ajout des appareils

Sur la page du plugin, le bouton **Synchroniser** (le démon doit être démarré) :

1. recherche les appareils sur le réseau local ;
2. si un compte MSmartHome est configuré, s'y connecte et récupère la liste des appareils du compte ;
3. pour chaque appareil V3 dont les clés ne sont pas encore connues, récupère le *token* et la *key* sur le cloud, puis les **vérifie directement auprès de l'appareil** avant de les enregistrer ;
4. crée les nouveaux équipements, ou met à jour l'adresse IP, le port et le protocole des équipements existants. Les noms et les clés déjà présents ne sont jamais modifiés.

Un message résume l'opération et signale les appareils pour lesquels les clés n'ont pas pu être obtenues. Les appareils d'un type non pris en charge sont ignorés. Sans compte MSmartHome, seule la recherche locale est faite.

![Page du plugin](../images/plugin_devices.png)

Le bouton **Ajouter** permet de créer un équipement à la main, par exemple pour un appareil situé sur un autre sous-réseau. Il faut alors renseigner vous-même l'identifiant, l'adresse IP et, pour un appareil V3, le *token* et la *key*.

## Équipement

![Équipement](../images/device_config.png)

- **Appareil Midea**
  - **Type d'appareil** : climatiseur, climatiseur commercial ou déshumidificateur.
  - **Identifiant de l'appareil** : identifiant Midea, renseigné automatiquement lors de la synchronisation.
- **Connexion locale**
  - **Adresse IP** et **Port** (6444 par défaut).
  - **Version du protocole** : V3 pour la plupart des appareils récents, V2 pour les plus anciens.
  - **Token** et **Key** : clés d'authentification des appareils V3, récupérées automatiquement.
  - **Récupérer token/key depuis le cloud** : redemande les clés de cet appareil au cloud et les vérifie, par exemple après une réinitialisation du module Wi-Fi. Sauvegardez l'équipement avant de l'utiliser.
- **Options**
  - **Intervalle d'interrogation** : laissez vide pour utiliser la valeur de la configuration du plugin.
- **Informations**
  - Numéro de série et modèle de l'appareil, en lecture seule.

> **Important**
>
> Conservez le *token* et la *key* de vos appareils V3 en lieu sûr. Ils permettent de continuer à piloter les appareils même si le cloud Midea devient indisponible.

## Commandes

Les commandes sont créées automatiquement selon les capacités remontées par chaque appareil. Leur liste détaillée sera ajoutée ici dès qu'elles seront disponibles.

## Dépannage

| Message | Solution |
|---|---|
| *Identifiant ou mot de passe MSmartHome incorrect* | Vérifiez le compte dans la configuration du plugin. Le plugin ne retente pas tant que les identifiants ne changent pas. |
| *Le cloud Midea a temporairement bloqué le compte* | Trop de connexions (codes `7610`, `65027`). Attendez le délai indiqué, sans relancer de synchronisation. |
| *appareil non appairé directement sur ce compte (partagé ?)* | Dans l'application MSmartHome, appairez l'appareil avec ce compte, pas seulement via un partage. |
| *appareil absent du compte MSmartHome* | L'appareil est sur le réseau mais dans un autre compte : saisissez *token* et *key* à la main, ou appairez-le avec ce compte. |
| *clés refusées par l'appareil* | Relancez **Récupérer token/key depuis le cloud** ; si le problème persiste, réappairez l'appareil dans l'application. |
| *appareil introuvable sur le réseau local* / *injoignable* | Vérifiez que l'appareil est allumé et sur le même réseau que Jeedom, ou renseignez l'**adresse de diffusion** de son réseau. |

## Crédits

Le plugin s'appuie sur les bibliothèques open source [msmart-ng](https://github.com/mill1000/midea-msmart) et [midea-local](https://github.com/midea-lan/midea-local).
