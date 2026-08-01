# Configuration et éditeur {#configuration-et-editeur}

## Profils, surcharges et configuration effective {#profils-surcharges-et-configuration-effective}

Un profil contient un tableau de bord complet. Un appareil référence un profil et peut conserver une surcharge. Celle-ci suit RFC 7396 : les objets fusionnent récursivement, les tableaux sont entièrement remplacés et `null` supprime une clé. Les liaisons de fournisseurs sont stockées séparément et ne sont jamais résolues en secrets.

```json
{
  "schema_version": 1,
  "theme": "dark",
  "tabs": [
    {
      "id": "overview",
      "title": "Vue d’ensemble",
      "columns": 2,
      "widgets": [{"id": "clock", "type": "clock"}]
    }
  ]
}
```

## Éditeurs JSON et visuel {#editeurs-json-et-visuel}

JSON est toujours la vue initiale. Des vues séparées présentent le brouillon du profil, la surcharge de l’appareil et la configuration effective en lecture seule. Enregistrer crée un brouillon ; seule l’action **Publier** valide les références, crée une révision monotone et la déploie. Un fournisseur absent bloque la publication. Une entité HA temporairement absente produit un avertissement.

L’éditeur visuel modifie thèmes, onglets, colonnes et widgets natifs courants. Les blocs inconnus ou complexes restent inchangés ; le retour à JSON ne perd donc aucun contenu avancé.

## Aperçu {#apercu}

Sélectionnez un appareil pour employer ses dernières dimensions physiques et utiles en pixels, la surface intérieure de l’activité, l’orientation, la densité, le DPI, l’échelle de police et les marges connues. L’aperçu convertit dp et sp avec ces valeurs et se redimensionne proportionnellement dans le navigateur. Portrait et paysage peuvent être choisis explicitement. Hors ligne, les dernières données sont utilisées ; la tablette générique est clairement non spécifique.

L’aperçu emploie les états HA actuels, mais reste approximatif car les moteurs de polices Android et navigateur diffèrent. L’appareil natif fait foi.

## Révisions et restauration {#revisions-et-restauration}

Vingt révisions immuables sont conservées. Une restauration ne réécrit pas l’historique : elle republie le contenu choisi sous une révision supérieure. Si l’application refuse une configuration, la dernière valide reste active et HA affiche la révision non acquittée.
