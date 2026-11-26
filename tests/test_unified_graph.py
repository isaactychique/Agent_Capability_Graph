"""Regression checks for corpus selection, identity merging and SHACL rejection."""
import copy
import json
from pathlib import Path
from datetime import date
import sys
import unittest

from pyshacl import validate
from rdflib import Graph, Namespace, RDF

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'src'))
from acg import build as unified
from acg.database import load_graph_inputs
from acg.selection import select_skills, load_selection
from acg.paths import REGISTRY

A = Namespace('urn:acg:ontology:')
S = Namespace('https://schema.org/')
P = Namespace('http://www.w3.org/ns/prov#')
SH = Namespace('http://www.w3.org/ns/shacl#')


class UnifiedCorpus(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.graph = Graph().parse(ROOT / 'data/processed/agent_capability_graph.ttl')
        cls.selection = json.loads(unified.SELECTION.read_text())
        cls.skills = load_graph_inputs()['all_skills']
        cls.originals = json.loads((ROOT / 'data/sources/expanded_sources.json').read_text())

    def test_requested_scope_and_no_duplicate_servers(self):
        self.assertEqual(len(set(self.graph.subjects(RDF.type, A.MCPServer))), 10)
        self.assertEqual(len(set(self.graph.subjects(RDF.type, A.AgentSkill))), 110)
        for identifier in ('filesystem', 'brave-search'):
            server = unified.entity_uri(identifier)
            self.assertIn((server, RDF.type, A.MCPServer), self.graph)
            self.assertEqual(len(set(self.graph.objects(server, S.name))), 1)
            self.assertEqual(len(set(self.graph.objects(server, P.wasDerivedFrom))), 2)
        for tool in self.graph.subjects(RDF.type, A.MCPTool):
            self.assertEqual(len(set(self.graph.subjects(A.exposesTool, tool))), 1)

    def test_initial_evidence_preserved(self):
        inputs = load_graph_inputs()
        collected = inputs['metadata']['collected_at']
        old = unified.curated_graph(inputs['curated'], date.fromisoformat(collected[:10]))
        self.assertTrue(set(old) <= set(self.graph))

    def test_selection_is_additional_and_independent_of_input_order(self):
        chosen, overlap, _ = select_skills(self.skills, self.originals['agent_skills'])
        replay, _, _ = select_skills(list(reversed(self.skills)), self.originals['agent_skills'])
        ids = [r['skill_id'] for r in chosen]
        self.assertEqual(len(set(ids)), 100)
        self.assertEqual(ids, [r['skill_id'] for r in replay])
        self.assertEqual(set(ids), {r['skill_id'] for r in self.selection['skills']})
        self.assertFalse(set(ids) & {r['skill_id'] for r in overlap})

    def test_changed_selected_record_requires_explicit_refresh(self):
        altered = copy.deepcopy(self.skills)
        chosen = {r['skill_id'] for r in self.selection['skills']}
        next(r for r in altered if r['skill_id'] in chosen)['description'] = 'Changed'
        with self.assertRaisesRegex(ValueError, 'changed or disappeared'):
            load_selection(altered, self.originals['agent_skills'])

    def test_merged_web_tool_has_registration_evidence(self):
        tool = next(self.graph.subjects(S.name, unified.Literal('brave_web_search')))
        self.assertEqual(len(set(self.graph.objects(tool, P.wasDerivedFrom))), 2)
        claims = list(self.graph.objects(tool, A.hasCapabilityAssertion))
        self.assertEqual(len(claims), 1)
        self.assertTrue(list(self.graph.objects(claims[0], A.basedOnSource)))

    def test_spreadsheet_query_groups_multiple_sources_for_one_skill(self):
        query = (ROOT / 'queries/skills_by_format.rq').read_text().replace('__FORMAT__', 'spreadsheet')
        answers = [row for row in self.graph.query(query) if str(row.skillName) == 'xlsx']
        self.assertEqual(len(answers), 1)
        self.assertIn('github.com/anthropics/skills', str(answers[0].evidence))
        self.assertIn('raw.githubusercontent.com/anthropics/skills', str(answers[0].evidence))

    def test_shacl_rejects_missing_name_parent_and_evidence(self):
        broken = Graph()
        broken += self.graph
        server = next(broken.subjects(RDF.type, A.MCPServer))
        tool = next(broken.subjects(RDF.type, A.MCPTool))
        claim = next(broken.subjects(RDF.type, A.CapabilityAssertion))
        broken.remove((server, S.name, None))
        broken.remove((None, A.exposesTool, tool))
        broken.remove((claim, A.basedOnSource, None))
        conforms, report, _ = validate(broken, shacl_graph=str(ROOT / 'ontology/shapes.ttl'), meta_shacl=True)
        self.assertFalse(conforms)
        self.assertTrue({server, tool, claim} <= set(report.objects(None, SH.focusNode)))


if __name__ == '__main__':
    unittest.main()
