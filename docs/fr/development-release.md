# Développement et versions

## Dépôt et tests

L’intégration réside dans `custom_components/rustyhama`. Les schémas neutres sont dans `schemas`, les vecteurs Python/Java partagés dans `test-vectors`. La CI de push exécute pytest, Ruff, MyPy, tests frontend et instantanés de viewport, Hassfest, validation HACS, parité documentaire et trois constructions Zensical strictes.

Vérifications locales principales :

```bash
python -m pytest
ruff check .
mypy custom_components/rustyhama
python scripts/check_docs.py
zensical build --clean --strict
zensical build --config-file zensical.en.toml --clean --strict
zensical build --config-file zensical.fr.toml --clean --strict
```

## Contrat de version

Application et intégration commencent à `0.1.0`. `1.0.0` marque le premier protocole conjointement stable. Un tag de version doit correspondre exactement à `manifest.json`. Forgejo fait autorité, publie les trois langues sous `daniel.snii.de/RustyHAMA-Integration/` et reflète commit et tag vers GitHub.

GitHub produit `rustyhama.zip` contenant le dossier complet `custom_components/rustyhama`. HACS installe uniquement des versions GitHub complètes. Une barrière de version teste installation, mise à jour, égalité des versions et contenu ZIP reproductible.

## Définition d’achèvement

Une fonction n’est achevée que si les tests de contrat Python, frontend et Android la couvrent, si les échecs sont exercés et si explications, exemples, tableaux et avertissements associés sont complets en allemand, anglais et français. Manifeste des pages, structure des titres, liens internes et couverture des champs JSON sont vérifiés automatiquement.
