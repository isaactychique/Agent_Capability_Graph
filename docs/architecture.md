# Architecture actuelle

Une commande, `pipeline.py`, pilote un seul graphe final.
Le code est dans `src/acg/` et les chemins principaux dans `src/acg/paths.py`.

## Parcours des données

```text
Échantillon initial                      Grand corpus du collègue
  data/sources/expanded_sources.json        metadata/data/raw/
        ↓ ingestion/curated.py                    ↓ ingestion/registry/
  data/interim/metadata.sqlite3             metadata/data/normalized/ et enriched/
        ↓ rdf/curated.py                          ↓ rdf/registry.py
        └────────────────────┬────────────────────┘
                         selection.py
                  config/corpus_selection.json
                             ↓
                           build.py
                 fusion des identités et preuves
                             ↓
                        capabilities.py
                config/capability_mappings.json
                             ↓
           data/processed/agent_capability_graph.ttl
                    ┌────────┼────────┐
                inventory   query   validation
                    └────────┼────────┘
                          reports/
```

## Rôle des dossiers

| Dossier | Contenu |
| --- | --- |
| `config/` | Uniquement la sélection du corpus et les correspondances de tâches |
| `ontology/` | Le vocabulaire RDF, le contrat SHACL structurel et le contrôle de couverture |
| `src/acg/` | Construction, sélection, annotations, inventaire, validation et requêtes |
| `src/acg/ingestion/` | Collecte et normalisation des sources |
| `src/acg/rdf/` | Conversion des observations et fiches sources en RDF |
| `data/` | Manifeste initial, preuves téléchargées, SQLite et graphe final |
| `metadata/data/` | Cache et JSONL du corpus élargi, conservés à leurs chemins d'origine |
| `reports/capabilities/` | Annotations, preuves, couverture et ressources non classées |
| `reports/corpus/` | Sélection, rapprochements d'identités et effectifs finaux |
| `reports/curated/` | CSV de consultation du corpus initial |
| `reports/registry/` | Statistiques et CSV du corpus source élargi, pas du seul graphe sélectionné |
| `reports/validation/unified/` | Rapports SHACL structurels et de couverture du graphe final |
| `archive/` | Historique conservé, absent du workflow actif |

Les JSONL et le SQLite alimentent les calculs. Les CSV sont des exports destinés
à la lecture : leur place est dans `reports/`, pas parmi les entrées de calcul.
Ne pas modifier les RDF ou CSV générés pour changer durablement les données.

## Commandes

```bash
python pipeline.py run
python pipeline.py query tools_for_web_search.rq
python pipeline.py query skills_by_format.rq --format PDF
python pipeline.py query skill_requirements.rq
```

`queries/query_rdf.py` reste un petit raccourci disponible à côté des `.rq` ;
il délègue au même code que `pipeline.py query`.
Les autres anciens lanceurs sont archivés et ne constituent plus des commandes actives.

## Actualiser les sources

La construction et les requêtes nécessitent seulement le `requirements.txt` principal.
La collecte et la normalisation utilisent des dépendances supplémentaires :

```bash
python -m pip install -r src/acg/ingestion/requirements.txt
python pipeline.py normalize                    # cache registry existant, sans réseau
python pipeline.py collect --source curated     # collecte réseau de l'échantillon initial
python pipeline.py collect --source registry    # collecte réseau du corpus élargi
```

La normalisation écrit les JSONL dans `metadata/data/`, les CSV dans
`reports/registry/tables/`, et les statistiques dans `reports/registry/`.
La collecte initiale écrit son SQLite dans `data/interim/` et son CSV dans
`reports/curated/metadata_comparison.csv`.

Après une actualisation, reconstruire et valider. Si une fiche sélectionnée a
changé, examiner la modification avant de lancer :

```bash
python pipeline.py build --refresh-selection
```

## Ce qui est archivé

`archive/` rassemble les anciens graphes séparés, configurations à deux corpus,
prototypes de recherche et de collecte pilote, vieux lanceurs, brouillons et
anciens rapports SHACL. `archive/cleanup_manifest.json` indique les déplacements.
Le collecteur pilote historique n'est plus proposé comme commande active : il
remplaçait le SQLite du projet par le tout petit échantillon de départ.

Les caches bruts, les JSONL et la sélection figée sont conservés. Les liens de
provenance et les empreintes des fiches sélectionnées restent ainsi valides.
