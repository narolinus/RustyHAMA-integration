# Entités et actions

## Entités de l’appareil

Chaque appareil possède un véritable `assist_satellite.*`. Les caméras activées créent `camera.*` ; `media_player.*` existe mais reste désactivé par défaut. Les réglages d’exécution utilisent `EntityCategory.CONFIG`, les diagnostics `EntityCategory.DIAGNOSTIC`.

Les capteurs actifs couvrent batterie, charge, source électrique, signal Wi-Fi, réseau et IP, onglet actif, en ligne/dernière vue, versions application/Android, durée de fonctionnement, stockage, géométrie d’écran et états économiseur, voix, caméra et service. Les capteurs disponibles de lumière, proximité, accélération, gyroscope, champ magnétique, pression, humidité, température, rotation et pas sont créés désactivés.

Interrupteurs, nombres et sélections règlent profil, luminosité, écran, voix/mot de réveil, VAD, route audio, économiseur, FPS/qualité/résolution/transport caméra, lecteur multimédia et intervalle des capteurs. Les boutons rechargent la configuration, réveillent l’écran ou redémarrent le service.

## Actions propres

| Action | Fonction |
|---|---|
| `rustyhama.send_notification` | surimpression si visible, notification système Android en arrière-plan |
| `rustyhama.set_active_tab` | sélectionner un onglet par index ou identifiant stable |
| `rustyhama.set_screensaver` | activer, désactiver ou inverser l’économiseur |
| `rustyhama.reload_configuration` | envoyer la dernière configuration publiée |

```yaml
action: rustyhama.send_notification
data:
  device_id: 0123456789abcdef
  title: Porte d’entrée
  message: Quelqu’un a sonné.
  play_sound: true
```

Les annonces et conversations utilisent les actions standard `assist_satellite` ; la lecture utilise `media_player`. Les widgets ne peuvent pas appeler des services HA arbitraires. L’intégration extrait les entités du tableau de bord effectif, transmet uniquement leurs états et autorise un ensemble fixe d’opérations typées par domaine.
