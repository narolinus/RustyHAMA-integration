# Modules fonctionnels {#modules-fonctionnels}

## Voix {#voix}

Le satellite Assist prend en charge `IDLE`, `LISTENING`, `PROCESSING` et `RESPONDING`, la détection serveur du mot de réveil, l’appui-pour-parler, le choix de pipeline et VAD, TTS, les annonces et les conversations démarrées ou poursuivies. Android diffuse du PCM mono 16 kHz par un flux authentifié éphémère. Les événements de pipeline et médias TTS reviennent par le canal de contrôle. L’inférence locale du mot de réveil reste une capacité future hors de 0.1.

## Caméra {#camera}

L’application annonce les caméras disponibles. L’assistant configure orientation, résolution, largeur maximale, FPS, qualité JPEG et transport. En mode direct par défaut, HA charge instantanés ou MJPEG par le HTTPS épinglé de l’appareil sur le LAN. Le mode tunnel transporte les images par des flux authentifiés éphémères. `camera.*` relaie le contenu via HA ; adresse et accès de l’appareil ne sont pas publiés.

## Lecteur multimédia et capteurs {#lecteur-multimedia-et-capteurs}

Le lecteur Android facultatif prend en charge URL/TTS, lecture/pause/arrêt, recherche, volume, muet, position, métadonnées et pochette. Il est désactivé par défaut puis peut être importé dans Music Assistant. Intervalles minimaux et seuils de variation limitent la charge réseau et Recorder. La localisation n’est ni demandée ni transmise.

## Fournisseurs {#fournisseurs}

Plusieurs connexions nommées Immich et Music Assistant sont possibles. Leurs secrets restent dans le stockage HA privé, sont masqués des diagnostics et ne vont jamais vers Android. Recherche et médias Immich passent côté serveur. Music Assistant utilise d’abord son intégration HA officielle, ses entités et actions ; seules les fonctions existantes manquantes relèvent d’un adaptateur serveur étroit.

## Compilation serveur du tableau de bord {#compilation-serveur-du-tableau-de-bord}

L’intégration résout `auto-entities` avant la transmission. Les règles include, exclude, zone, appareil, intégration, label, état, attribut, glob et expression régulière, ainsi que le tri, s’exécutent dans HA ; Android ne reçoit que la liste `entities` finale triée et ses états. Lors d’un changement d’état, les requêtes dynamiques d’un appareil sont regroupées puis réévaluées sur 250 ms. Si le résultat change, l’appareil reçoit la configuration mise à jour et un instantané d’état minimal actualisé. Sans changement, le canal de contrôle reste silencieux. Hors ligne, Android rend la dernière liste activée avec succès.

## Parité du tableau de bord {#parite-du-tableau-de-bord}

Thèmes, onglets, badges, conditions, grilles imbriquées, graphiques, modifications de calendrier, groupes multimédias, économiseur, vues Immich, onglet Music Assistant, bouton vocal, contrôle des états HA et toutes les familles et alias documentés de l’application restent disponibles.
