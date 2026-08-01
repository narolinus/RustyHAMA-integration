# Installation et association

## Prérequis

- Home Assistant Core 2026.7 ou plus récent
- un point d’accès HTTPS joignable par la tablette et le navigateur
- l’application RustyHAMA 0.1 ou plus récente
- les droits administrateur pour l’installation et le panneau

## Installation HACS

Ouvrez HACS, ajoutez le dépôt GitHub public comme dépôt personnalisé de type « Intégration », installez RustyHAMA et redémarrez Home Assistant. Ajoutez ensuite **RustyHAMA** dans **Paramètres → Appareils et services**. L’entrée de service n’existe qu’une fois ; les appareils sont ajoutés depuis le panneau latéral.

## Préparer un appareil

Ouvrez **RustyHAMA → Appareils**, saisissez un nom, un profil et éventuellement l’identifiant de zone HA, puis créez l’association. Le code à huit chiffres est valable dix minutes et tolère au maximum cinq erreurs. Le QR code contient l’URL HA et un jeton unique à forte entropie ; l’empreinte du certificat y figure lorsqu’elle est disponible.

Saisissez l’URL et le code dans l’application ou scannez le QR code. Après l’association, Android conserve l’identifiant aléatoire de 256 bits dans le stockage privé exclu des sauvegardes. Home Assistant n’enregistre que son condensat.

## Certificats

Les certificats publiquement reconnus sont vérifiés avec Conscrypt et le jeu d’autorités maintenu avec la version. Pour un certificat autosigné ou inconnu d’une ancienne tablette, l’application affiche son empreinte SHA-256. Comparez-la à Home Assistant par un second canal fiable avant de choisir **Faire confiance et épingler**.

!!! danger
    Ne confirmez jamais un changement d’empreinte inattendu. Révoquez l’appareil dans le panneau, examinez le certificat HA et le DNS, puis réassociez uniquement après résolution.

## Après l’association

L’appareil HA affiche l’état en ligne, la révision de configuration et les caractéristiques d’écran. Affectez une zone si aucune n’a été choisie. N’activez le lecteur multimédia ou les capteurs matériels désactivés par défaut qu’en cas de besoin. L’identifiant peut être renouvelé dans le panneau ; supprimer l’appareil coupe immédiatement sa connexion.
