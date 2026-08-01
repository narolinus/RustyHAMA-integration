# Protocole et sécurité {#protocole-et-securite}

## Points d’accès {#points-dacces}

| Point d’accès | Fonction |
|---|---|
| `POST /api/rustyhama/v1/pair` | association unique sans jeton utilisateur HA |
| `/api/rustyhama/v1/device/ws` | canal de contrôle permanent |
| `/api/rustyhama/v1/device/streams/{session_id}` | flux voix, caméra et médias |

Chaque message porte version du protocole, ID, type, horodatage, révision et charge utile. Les ID servent aux accusés, à la déduplication et aux délais. Une nouvelle génération de session remplace sans ambiguïté l’ancienne connexion.

## Comportement de connexion {#comportement-de-connexion}

Les pulsations détectent les WebSockets à demi ouverts. La reconnexion applique un délai exponentiel avec aléa. Files bornées et canaux de flux séparés protègent le contrôle de la contre-pression. Notifications et actions sont jetées hors ligne et jamais rejouées tardivement. Seuls l’état désiré et la dernière configuration convergent après reconnexion.

## Limite d’autorisation {#limite-dautorisation}

L’identifiant d’appareil authentifie exactement un appareil. Il est aléatoire, révocable et renouvelable ; HA ne conserve que SHA-256. Un appareil ne peut pas envoyer d’appel libre de service. Entité et opération doivent figurer dans le tableau de bord effectif ou la liste autorisée du serveur. Les secrets de fournisseurs sont masqués récursivement avant journaux et diagnostics.

## TLS et protection de l’hôte {#tls-et-protection-de-lhote}

La communication accepte uniquement HTTPS/WSS. Les certificats publics sont vérifiés normalement. Un certificat inconnu exige une confirmation manuelle de l’empreinte puis est épinglé ; tout changement coupe la connexion. La sauvegarde Android est désactivée. Le chiffrement des disques et sauvegardes HA relève de l’hôte.

!!! note
    Le protocole devient conjointement stable à `1.0.0`. Avant cela, les versions restent négociées strictement ; versions inconnues et charges invalides sont refusées.
