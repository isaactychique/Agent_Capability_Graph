# Agent Capability Graph

Projet EURECOM : un seul graphe RDF pour les serveurs MCP, leurs outils et les
Agent Skills, avec des tâches normalisées et leurs preuves.

## Lancer le projet

Depuis la racine :

```bash
metadata/.venv/bin/python pipeline.py run
```

La commande construit le graphe, affiche sa couverture et exécute SHACL, sans accès
réseau. Elle utilise le SQLite initial et les JSONL normalisés déjà présents.
Pour un autre environnement : `python -m pip install -r requirements.txt`, puis
utiliser `python` à la place de `metadata/.venv/bin/python`.

## Les fichiers utiles au quotidien

| Besoin | Fichier |
| --- | --- |
| Lire le graphe final | `data/processed/agent_capability_graph.ttl` |
| Voir les 100 Skills sélectionnés | `config/corpus_selection.json` |
| Examiner les correspondances de tâches | `config/capability_mappings.json` |
| Examiner les annotations et leurs preuves | `reports/capabilities/review.csv` |
| Voir les ressources non classées | `reports/capabilities/unclassified.csv` |
| Lire les contrôles SHACL | `reports/validation/unified/` |

Le graphe contient **10 serveurs, 55 outils et 110 Skills**. Parmi eux, 10 serveurs,
55 outils et 109 Skills ont une annotation candidate. `template-skill` reste non
classé car sa description est provisoire. Les annotations attendent une revue humaine.

## Une commande principale

```bash
metadata/.venv/bin/python pipeline.py build
metadata/.venv/bin/python pipeline.py inventory
metadata/.venv/bin/python pipeline.py validate
metadata/.venv/bin/python pipeline.py query tools_for_web_search.rq
metadata/.venv/bin/python pipeline.py query skills_by_format.rq --format PDF
metadata/.venv/bin/python pipeline.py query entity_capabilities.rq --name pdf
```

`pipeline.py --help` liste les commandes. Les fichiers SPARQL restent dans `queries/`.
`validate --strict` échoue aussi pour une couverture incomplète ; le cas
`template-skill` provoque donc cet échec attendu.

## Organisation

```text
pipeline.py   Commande principale
src/acg/      Code Python
config/       Deux configurations actives : sélection et tâches
ontology/     Ontologie et contraintes SHACL
queries/      Requêtes SPARQL
data/         Données du corpus initial et graphe final
metadata/     Données sources du collègue et environnement Python existant
reports/      Tableaux de consultation et résultats générés
tests/        Tests
docs/         Explications actuelles et rapports de référence
archive/      Historique retiré du workflow courant
```

Les fichiers JSONL de `metadata/data/` et le SQLite de `data/interim/` sont des
entrées de calcul. Leurs CSV de consultation sont dans `reports/curated/` et
`reports/registry/tables/`. Le corpus source complet contient davantage de ressources
que le graphe sélectionné ; il est conservé avec les preuves pour la reproductibilité.

Les anciens lanceurs, prototypes, configurations à deux graphes et brouillons
sont réunis dans `archive/`. Ils ne sont pas lus par le workflow courant.
Le détail des déplacements est dans `archive/cleanup_manifest.json`.

Pour aller plus loin :

- [Architecture et actualisation des sources](docs/architecture.md)
- [Capacités, preuves et revue](docs/capabilities.md)
- [Validation SHACL](docs/validation.md)
- [Requêtes SPARQL](queries/README.md)

## Full GitSkills metadata analysis

The full-corpus analysis extends the original 180-row sample at a pinned dataset
revision. Code is in `src/acg/ingestion/gitskills/`, aggregate results are in
`reports/gitskills/`, and tests are in `tests/test_gitskills*.py`.
See [results, counting definitions and reproduction commands](reports/gitskills/README.md).
Raw downloads and full derived tables remain outside Git. This analysis does not
change the selected RDF corpus or existing source snapshots.
