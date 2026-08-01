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

JSON est toujours la vue initiale. L’éditeur de code fournit la coloration syntaxique, les numéros de ligne, l’indentation par tabulation et la validation syntaxique immédiate. Des vues séparées présentent le brouillon du profil, la surcharge de l’appareil et la configuration effective en lecture seule. Enregistrer un profil crée un brouillon ; seule l’action **Publier** valide les références, crée une révision monotone et la déploie. Enregistrer une surcharge d’appareil publie et déploie immédiatement son correctif de fusion. Un fournisseur absent bloque la publication. Une entité HA temporairement absente produit un avertissement.

L’éditeur visuel modifie des profils complets. Il expose les véritables champs de thème pour les couleurs, le rayon, l’échelle, le remplissage et l’espacement, ainsi que les onglets, positions de grille, étendues et types de widgets natifs courants. Les widgets peuvent être créés, réordonnés et supprimés. Les champs non affichés et les blocs complexes restent inchangés. Les surcharges d’appareil sont des correctifs de fusion RFC 7396 et restent donc dans l’éditeur JSON ; leur résultat fusionné est visible à droite.

## Aperçu {#apercu}

Sélectionnez un appareil pour employer ses dernières dimensions physiques et utiles en pixels, la surface intérieure de l’activité, l’orientation, la densité, le DPI, l’échelle de police et les marges connues. L’aperçu convertit dp et sp avec ces valeurs et se redimensionne proportionnellement dans le navigateur. Portrait et paysage peuvent être choisis explicitement. Hors ligne, les dernières données sont utilisées ; la tablette générique est clairement non spécifique.

L’aperçu emploie les états HA actuels, la véritable famille de widgets, l’ordre des onglets, les lignes et colonnes explicites, les étendues, les hauteurs de cellule et les valeurs du thème. `auto_entities` est résolu par le même compilateur côté serveur que celui utilisé pour le déploiement vers Android. Il reste néanmoins approximatif, car les moteurs de polices et de médias Android et du navigateur diffèrent. L’appareil natif fait foi. L’en-tête renvoie directement vers la documentation complète des widgets avec tous les codes JSON.

## Révisions et restauration {#revisions-et-restauration}

Vingt révisions immuables sont conservées. Une restauration ne réécrit pas l’historique : elle republie le contenu choisi sous une révision supérieure. Si l’application refuse une configuration, la dernière valide reste active et HA affiche la révision non acquittée.
