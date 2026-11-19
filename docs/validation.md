# Validation SHACL

```bash
metadata/.venv/bin/python pipeline.py validate
metadata/.venv/bin/python pipeline.py validate --strict
```

Le code est dans `src/acg/validation.py` et les formes dans `ontology/`.
Le moteur pySHACL valide aussi les formes avec Meta-SHACL. Aucun raisonnement OWL
n'est activé. Un graphe sans serveur MCP est refusé.

`shapes.ttl` exige noms uniques, sources, parents des outils, tâches normalisées,
méthodes et statuts des assertions. Les assertions dérivées d'un serveur doivent
pointer vers une assertion de même tâche sur un de ses outils exposés.

`coverage.ttl` signale séparément les serveurs, outils et Skills sans assertion.
Cette absence signifie une classification manquante, pas une incapacité de la ressource.
Le graphe conserve un cas explicite : `template-skill`, avec une description provisoire.

Les fichiers `reports/validation/unified/report.txt` et `report.ttl` concernent la
structure ; `coverage.txt` et `coverage.ttl` concernent la couverture.
Sans `--strict`, seule une erreur structurelle entraîne un code 1.
Avec `--strict`, une ressource non classée entraîne également un code 1.
Aucun de ces contrôles ne transforme une annotation candidate en annotation revue.

Les tests sont regroupés dans `tests/`. Installer les dépendances principales et
celles de `src/acg/ingestion/requirements.txt` pour la suite complète, puis lancer :

```bash
python -m unittest discover -s tests -v
```
