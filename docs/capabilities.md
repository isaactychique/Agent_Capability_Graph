# Capacités et revue

## Modèle des tâches

Une capacité décrit une **tâche**, par exemple `process / PDF document` ou
`search / web`. Le Skill ou l'outil est une ressource ; l'assertion est l'association
sourcée entre cette ressource et la tâche. Le modèle garde la méthode et le statut :

```text
Skill pdf ── assertion candidate ── process PDF document
                    └── passage de description + source SKILL.md

Brave Search ── assertion dérivée ── search web
                    └── assertion de brave_web_search + sa source
```

Les 17 assertions issues des registrations statiques sont conservées.
Les autres outils et Skills reçoivent une première tâche principale à partir de
**correspondances explicites** dans `config/capability_mappings.json`. Chaque
correspondance doit retrouver un passage de sa propre description source.
Le nom seul ne suffit pas ; une correspondance sans preuve reste non classée.
Les correspondances sont proposées par le projet et marquées
`candidate_for_human_review`, même quand la description source est explicite.
Les capacités d'un serveur sont dérivées de celles de ses outils avec les liens
`acg:derivedFromAssertion` ; cela ne constitue pas une vérification d'exécution.

Après le dernier enrichissement :

- 10/10 serveurs avec annotations dérivées de leurs outils ;
- 55/55 outils avec au moins une annotation candidate ;
- 109/110 Skills avec une annotation candidate ;
- `template-skill` reste non classé : sa description est un texte à remplacer.

`Reviewed: 0` indique qu'aucune annotation n'a été validée par une revue humaine.
Les chiffres mesurent une couverture initiale, pas l'ensemble des capacités de
chaque ressource. Les opérations précises, formats, exclusions et prérequis peuvent
encore nécessiter une annotation plus fine.

Pour examiner les annotations et leur preuve :

- `reports/capabilities/review.csv` : tâches, méthodes, citations, sources et supports ;
- `reports/capabilities/unclassified.csv` : ressources sans correspondance justifiée ;
- `reports/capabilities/coverage.json` : couverture détaillée par type.


La revue humaine doit vérifier la tâche, le passage cité, ses restrictions et la source.
`reports/capabilities/review.csv` est généré : les décisions de revue persistantes
ne sont pas encore importées par le pipeline. Ne pas modifier ce rapport pour
enregistrer durablement une décision.
