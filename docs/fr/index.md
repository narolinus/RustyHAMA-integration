# Intégration RustyHAMA

RustyHAMA connecte des tablettes murales Android à partir de l’API 17 comme appareils natifs à Home Assistant 2026.7 ou plus récent. L’intégration est la source centrale des tableaux de bord, profils, réglages d’appareil, connexions de fournisseurs et commandes. Une tablette ne reçoit ni jeton utilisateur Home Assistant général, ni clé de fournisseur.

Chaque tablette associée est enregistrée comme sous-entrée de configuration et appareil HA distincts. La zone HA choisie pour l’appareil constitue également le contexte de pièce du satellite Assist. L’intégration fournit un satellite Assist, des caméras et un lecteur multimédia facultatifs, ainsi que des entités capteur, capteur binaire, interrupteur, nombre, sélection et bouton.

## Principes directeurs

| Principe | Mise en œuvre |
|---|---|
| Association sûre | HTTPS, code à usage unique ou jeton QR éphémère, identifiant d’appareil révocable |
| Configuration centrale | Profils et correctif de fusion RFC 7396 propre à l’appareil |
| Activation atomique | Brouillon, validation, publication, accusé de l’appareil et dernière révision valide |
| Moindre privilège | Uniquement les états requis et des opérations typées autorisées côté serveur |
| Documentation égale | Allemand, anglais et français avec la même structure de pages |

## Bien démarrer

Commencez par [Installation et association](installation-pairing.md). La page [Configuration et éditeur](configuration-editor.md) décrit les tableaux de bord. En cas d’échec, consultez [Exploitation et dépannage](operations.md) et les diagnostics de l’intégration.

!!! warning
    L’architecture 0.1 ne migre pas les anciens fichiers `/local/*.json`, jetons utilisateur, webhooks ou événements globaux. HTTP et la désactivation générale des erreurs de certificat ne sont pas pris en charge.
