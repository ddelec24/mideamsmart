# Changelog plugin Midea MSmart

>**IMPORTANT**
>
>S'il n'y a pas d'information sur la mise à jour, c'est que celle-ci concerne uniquement de la mise à jour de documentation, de traduction ou de texte.

# 16/10/2026

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
