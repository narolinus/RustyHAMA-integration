# Exploitation et dépannage

## Fonctionnement normal

Le service Android de premier plan démarre après l’amorçage par défaut et maintient canal d’appareil, voix, caméra et médias. Sans HA, l’application poursuit avec sa dernière configuration acquittée ; les contrôles dépendant de HA indiquent indisponible. Dans HA, `config_revision` et `acknowledged_revision` comparent état désiré et confirmé.

## Séquence de diagnostic

1. Vérifiez en ligne/dernière vue et l’état du service sur l’appareil HA.
2. Comparez révision de configuration et accusé de l’appareil.
3. Vérifiez URL HTTPS, DNS, validité du certificat et empreinte épinglée.
4. Ouvrez les diagnostics masqués ; clés de fournisseurs et condensats d’identifiants doivent être absents.
5. Pour la voix, vérifiez permission micro, pipeline, STT/TTS et VAD.
6. Pour la caméra, vérifiez orientation, résolution, FPS, accès LAN et transport.

## Échecs fréquents

| Symptôme | Cause et action |
|---|---|
| Code refusé | expiré, consommé ou limite d’essais atteinte ; créer un nouveau code |
| Empreinte modifiée | ne pas confirmer ; examiner certificat et attaque proxy/DNS possible |
| Révision non acquittée | schéma ou référence refusé par l’application ; consulter les journaux ; la dernière valide reste active |
| Widgets indisponibles | appareil hors ligne ou entité temporairement absente de HA |
| Assist reste en écoute | vérifier format audio, fin de flux, VAD et pipeline STT |
| Caméra inaccessible | vérifier le chemin HTTPS direct ou choisir le transport tunnel |

## Révocation et récupération

Supprimez un appareil perdu dans le panneau : session, identifiant, sous-entrée et appareil HA sont révoqués. Réinstaller l’application exige une nouvelle association car la sauvegarde est désactivée. Restaurer une configuration crée toujours une nouvelle révision sans modifier l’historique antérieur.
