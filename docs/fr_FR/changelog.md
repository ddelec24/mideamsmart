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
