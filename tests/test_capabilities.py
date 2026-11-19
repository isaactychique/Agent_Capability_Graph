"""Checks against unsupported task labels and broken server derivations."""
from pathlib import Path
import sys
import unittest

from pyshacl import validate
from rdflib import Graph, Literal, Namespace, RDF, URIRef

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from acg.capabilities import add_candidate
from acg.inventory import coverage
from acg.paths import GRAPH, SHAPES, COVERAGE_SHAPES

A = Namespace('urn:acg:ontology:')
S = Namespace('https://schema.org/')
SH = Namespace('http://www.w3.org/ns/shacl#')


class TaskAnnotations(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.graph = Graph().parse(GRAPH)

    def test_evidence_must_match_and_names_alone_are_insufficient(self):
        graph = Graph()
        entity, source = URIRef('urn:test:skill'), URIRef('urn:test:source')
        rule = {'action':'process', 'object':'PDF document', 'evidence_pattern':'PDF files'}
        self.assertFalse(add_candidate(graph, entity, rule, 'test', 'Only processes images.', source, 'test'))
        self.assertEqual(len(graph), 0)
        self.assertTrue(add_candidate(graph, entity, rule, 'test', 'Process PDF files.', source, 'test'))
        claim = graph.value(entity, A.hasCapabilityAssertion)
        self.assertEqual(graph.value(claim, A.reviewStatus), Literal('candidate_for_human_review'))
        self.assertEqual(graph.value(claim, A.evidenceText), Literal('PDF files'))

    def test_template_is_unclassified_and_reported_by_coverage_shacl(self):
        template = next(self.graph.subjects(S.name, Literal('template-skill')))
        self.assertFalse(list(self.graph.objects(template, A.hasCapabilityAssertion)))
        conforms, report, _ = validate(self.graph, shacl_graph=str(COVERAGE_SHAPES))
        self.assertFalse(conforms)
        self.assertEqual(set(report.objects(None, SH.focusNode)), {template})
        stats = coverage(self.graph)
        self.assertEqual(stats['AgentSkill']['unclassified'], 1)
        self.assertEqual(stats['AgentSkill']['reviewed'], 0)

    def test_server_claims_are_derived_from_exposed_tools(self):
        for server in self.graph.subjects(RDF.type, A.MCPServer):
            exposed = set(self.graph.objects(server, A.exposesTool))
            for derived in self.graph.objects(server, A.hasCapabilityAssertion):
                task = self.graph.value(derived, A.assertedCapability)
                supports = list(self.graph.objects(derived, A.derivedFromAssertion))
                self.assertTrue(supports)
                self.assertEqual(self.graph.value(derived, A.assertionMethod), A.inferred)
                for claim in supports:
                    self.assertTrue(set(self.graph.subjects(A.hasCapabilityAssertion, claim)) & exposed)
                    self.assertEqual(self.graph.value(claim, A.assertedCapability), task)

    def test_shacl_rejects_a_server_claim_supported_by_an_unrelated_tool(self):
        graph = Graph(); graph += self.graph
        derived = next(graph.subjects(A.derivedFromAssertion, None))
        task = graph.value(derived, A.assertedCapability)
        other = next(claim for tool in graph.subjects(RDF.type, A.MCPTool)
                     for claim in graph.objects(tool, A.hasCapabilityAssertion)
                     if graph.value(claim, A.assertedCapability) != task)
        graph.remove((derived, A.derivedFromAssertion, None))
        graph.add((derived, A.derivedFromAssertion, other))
        conforms, report, _ = validate(graph, shacl_graph=str(SHAPES))
        self.assertFalse(conforms)
        self.assertIn(derived, set(report.objects(None, SH.focusNode)))

    def test_web_query_does_not_confuse_fetch_or_documentation_search(self):
        result = list(self.graph.query((ROOT / 'queries/tools_for_web_search.rq').read_text()))
        self.assertEqual(len(result), 1)
        self.assertEqual(str(result[0].toolName), 'brave_web_search')


if __name__ == '__main__':
    unittest.main()
