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

![Configuration du plugin](../images/plugin_config.png)

- **Compte MSmartHome**
  - **Identifiant (email)** et **Mot de passe** du compte MSmartHome.
- **Réseau local**
  - **Adresse de diffusion** : adresse(s) de broadcast utilisée(s) pour découvrir les appareils, séparées par des virgules. La valeur par défaut `255.255.255.255` convient dans la plupart des cas. Si les appareils ne sont pas trouvés, indiquez l'adresse de broadcast de votre réseau (par exemple `192.168.1.255`).
  - **Intervalle d'interrogation par défaut** : délai en secondes entre deux lectures de l'état des appareils (30 s par défaut, 10 s minimum).
- **Démon**
  - **Port du démon** : port local utilisé par le démon (55114 par défaut). Ne le modifiez qu'en cas de conflit avec un autre plugin.

## Ajout des appareils

Sur la page du plugin, le bouton **Synchroniser** récupère les appareils du compte MSmartHome, les recherche sur le réseau local et crée les équipements correspondants.

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
- **Options**
  - **Intervalle d'interrogation** : laissez vide pour utiliser la valeur de la configuration du plugin.
- **Informations**
  - Numéro de série et modèle de l'appareil, en lecture seule.

> **Important**
>
> Conservez le *token* et la *key* de vos appareils V3 en lieu sûr. Ils permettent de continuer à piloter les appareils même si le cloud Midea devient indisponible.

## Commandes

Les commandes sont créées automatiquement selon les capacités remontées par chaque appareil. Leur liste détaillée sera ajoutée ici dès qu'elles seront disponibles.

## Crédits

Le plugin s'appuie sur les bibliothèques open source [msmart-ng](https://github.com/mill1000/midea-msmart) et [midea-local](https://github.com/midea-lan/midea-local).
