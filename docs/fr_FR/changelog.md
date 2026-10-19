# Changelog plugin Midea MSmart

>**IMPORTANT**
>
>S'il n'y a pas d'information sur la mise à jour, c'est que celle-ci concerne uniquement de la mise à jour de documentation, de traduction ou de texte.

# 19/10/2026

- Version bêta 0.10.0
- Nouvelle **programmation** horaire : profils communs à tous les appareils (*Normal* et *Vacances* par défaut, modifiables), créneaux propres à chaque appareil (jours, heure, allumer ou éteindre, mode, consigne, ventilation, préréglage ou humidité)
- Nouvel équipement *Programmation*, ouvert par la tuile du même nom : sa commande *Choisir le profil* bascule tous les appareils d'un coup, par exemple depuis un scénario de vacances
- Rattrapage du dernier créneau passé au changement de profil, à la reprise de la programmation ou au redémarrage de Jeedom (désactivable par appareil)
- Nouvelles commandes *Suivre la programmation* et *Suspendre la programmation* sur chaque appareil
- Déshumidificateur : plusieurs commandes envoyées à la suite (par exemple mode puis humidité) ne s'annulent plus

# 17/10/2026

- Version bêta 0.9.2
- Correction du bouton **Copier pour le forum** du diagnostic quand Jeedom est ouvert en HTTP sur le réseau local. Si le navigateur refuse la copie, le texte s'affiche, sélectionné, pour être copié à la main
- Date de dernière communication de l'équipement mise à jour à chaque interrogation réussie, même quand aucune valeur ne change : l'équipement n'est plus signalé à tort avec le *délai maximum entre deux communications* de Jeedom
- Commande *Dégivrage en cours* créée seulement si l'appareil remonte cette information. Pour retirer celle déjà créée, cliquez sur **Mettre à jour les commandes**
- Diagnostic complété : durée de vie des connexions et état de la demande des capacités
- Version bêta 0.9.1
- Crédits : auteurs du plugin précisés (ddelec24, chef d'orchestre ; Claude, co-auteur) dans la documentation, la licence et la fiche du plugin
- Nouvelle option **Durée de vie des connexions** (90 s par défaut), remède aux appareils qui coupent eux-mêmes la connexion (erreurs *Transport is closing or closed* et *failed CRC and checksum*)
- Demande ou commande renvoyée une fois sur une nouvelle connexion quand l'appareil coupe la connexion, et appareil déclaré hors ligne seulement après deux échecs consécutifs
- Ces erreurs de la bibliothèque sont journalisées en warning
- Capacités redemandées rapidement si l'appareil ne les a pas envoyées, avec ajustement automatique des commandes à leur réception (commandes en trop, comme *Filtre à nettoyer*, sur un seul appareil)
- Indicateur de l'état des capacités sur la page de l'équipement
- Correction d'une erreur à l'arrêt d'un déshumidificateur

# 16/10/2026

- Première version bêta (0.9.0), à tester avec de vrais appareils : vos retours sont les bienvenus sur le forum
- Création du plugin : structure de base, page de configuration et page des équipements
- Installation des dépendances : Python 3.13 autonome (via uv) et environnement virtuel dédié au plugin
- Démon Python (asyncio) : démarrage, arrêt propre, communication avec Jeedom et transmission de la liste des équipements
- Synchronisation des appareils : compte MSmartHome, recherche sur le réseau local, création et mise à jour des équipements
- Récupération du token et de la key, vérifiés auprès de l'appareil, et bouton pour les redemander
- Protection contre le blocage du compte Midea (codes 7610 et 65027)
- Adresse de diffusion automatique par défaut (toutes les interfaces réseau)
- Pilotage local des climatiseurs (AC) et climatiseurs commerciaux (CC) avec msmart-ng : état, interrogation périodique, appareil hors ligne
- Commandes créées selon les capacités de chaque appareil, avec codes stables pour les scénarios et bouton de mise à jour
- Options d'équipement : bip, pas de consigne, consommation électrique
- Pilotage local des déshumidificateurs (A1) avec midea-local : mode, ventilation, consigne d'humidité, réservoir, oscillation, ioniseur, pompe, verrouillage enfant, filtre
- Alertes réservoir plein et filtre affichées par une icône verte ou rouge
- Fenêtre de diagnostic par équipement, avec copie d'un résumé sans secret pour le forum
- Recherche automatique sur le réseau local des appareils qui ont changé d'adresse IP
- Blocages du cloud et mot de passe refusé mémorisés, même après redémarrage du démon
- Equipement signalé en timeout quand l'appareil ne répond plus, page Santé et informations pour le forum
