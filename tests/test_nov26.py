import hashlib
import json
from pathlib import Path
import unittest
from rdflib import Graph, Namespace, Literal, RDF
from src.acg.ingestion.gitskills.value_analysis import groups
ROOT=Path(__file__).resolve().parents[1]
A=Namespace('urn:acg:ontology:'); E=Namespace('https://example.org/acg-test/')

def blob(s):
    b=s.encode(); return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()

class ValueTests(unittest.TestCase):
    def test_grouping(self):
        self.assertEqual(groups('user-invocable',False),['false'])
        self.assertEqual(groups('user-invocable','false'),['non_boolean:string'])
        self.assertEqual(groups('tags',['PDF','pdf',' code ']),['code','pdf'])
        self.assertEqual(groups('version','1.2.3'),['three_part_version_like'])
        self.assertEqual(groups('version',1.2),['numeric_yaml'])
        self.assertEqual(set(groups('allowed-tools','Bash(git status) Read')),{'shell','file_read'})
    def test_hash_is_byte_identity(self):
        self.assertNotEqual(blob('abc'),blob('abc\n'))
        self.assertNotEqual(blob('abc\n'),blob('abc\r\n'))
        self.assertEqual(blob('abc'),blob('abc'))

class QueryTests(unittest.TestCase):
    def test_positive_and_negative_cases(self):
        records=json.loads((ROOT/'docs/nov26/lin_queries.json').read_text())
        for rec in records:
            with self.subTest(cq=rec['id']):
                g=Graph().parse(ROOT/'tests/fixtures/nov26/query_fixture.ttl')
                if 'fields' in rec:
                    for obs,subject,field in [(E.obs,E.one,rec['fields'][0]),(E.noise,E.tool,rec['fields'][0]),(E.wrong,E.two,'unrelated')]:
                        for p,o in [(RDF.type,A.MetadataObservation),(A.observesEntity,subject),(A.observedFieldName,Literal(field)),(A.reviewedSource,E.source),(A.hasObservedValue,Literal('fixture value')),(A.observationStatus,A.present)]: g.add((obs,p,o))
                query=(ROOT/rec['query']).read_text(); rows=list(g.query(query))
                self.assertEqual(len(rows),1)
                if 'fields' in rec:
                    self.assertEqual(rows[0].asdict()['skill'],E.one)
                    # A checked but undocumented field remains visible, unbound value.
                    g.remove((E.obs,A.hasObservedValue,None)); g.set((E.obs,A.observationStatus,A.notDocumented))
                    rows=list(g.query(query)); self.assertEqual(len(rows),1)
                    self.assertNotIn('value',rows[0].asdict())
                    g.remove((E.obs,A.reviewedSource,None)); self.assertEqual(len(list(g.query(query))),0)
                elif rec['id']=='CQ19':
                    g.remove((E.claim,A.basedOnSource,None)); self.assertEqual(len(list(g.query(query))),0)
                else:
                    g.set((E.two,Namespace('https://schema.org/').name,Literal('different')))
                    self.assertEqual(len(list(g.query(query))),0)

class PromptTests(unittest.TestCase):
    def test_response_gate(self):
        from src.acg.capability_prompt import validate_response
        import copy
        vocab={'version':'v1','concepts':[{'uri':'https://example.org/pdf'}]}
        resource={'resource_id':'s1','description':'Extract PDF text.'}
        valid={'resource_id':'s1','vocabulary_version':'v1','status':'classified','assignments':[{'concept_uri':'https://example.org/pdf','evidence':'Extract PDF text.'}],'suggestions':[],'reason':'Explicit task'}
        self.assertEqual(validate_response(valid,vocab,resource),valid)
        for key,value in [('concept_uri','https://example.org/invented'),('evidence','Invented evidence')]:
            bad=copy.deepcopy(valid);bad['assignments'][0][key]=value
            with self.assertRaises(ValueError): validate_response(bad,vocab,resource)
        bad=copy.deepcopy(valid);bad['status']='unclassified'
        with self.assertRaises(ValueError): validate_response(bad,vocab,resource)
    def test_direct_projection_is_not_lost_or_given_false_provenance(self):
        g=Graph().parse(ROOT/'tests/fixtures/nov26/query_fixture.ttl')
        g.add((E.one,A.allowedTool,Literal('Read')))
        rows=list(g.query((ROOT/'queries/nov26/cq15_allowed_tools.rq').read_text()))
        self.assertEqual(len(rows),1)
        self.assertEqual(str(rows[0].asdict()['representation']),'direct_projection')
        self.assertNotIn('source',rows[0].asdict())

class AggregateEvidenceTests(unittest.TestCase):
    def test_value_counts_reconcile_with_existing_baseline(self):
        import csv
        from collections import Counter
        base=ROOT/'reports/gitskills'; new=base/'values-2026-11-26'
        def rows(p):
            with p.open() as f:return list(csv.DictReader(f))
        summary={(r['scope'],r['field']):int(r['present_contents']) for r in rows(new/'field_summary.csv')}
        totals=Counter()
        for r in rows(base/'frontmatter_fields.csv'):
            key=(r['scope'],r['field'])
            if key in summary:totals[key]+=int(r['unique_contents'])
        self.assertEqual(dict(totals),summary)
        for r in rows(new/'value_groups.csv'):
            self.assertLessEqual(int(r['contents']),summary[(r['scope'],r['field'])])
        m=json.loads((new/'manifest.json').read_text())
        self.assertTrue(m['baseline_field_type_reconciliation'])
        self.assertEqual(sum(m['parse_status'].values()),1877981)
        self.assertEqual(m['parse_status']['hash_mismatch'],42)

class VocabularyContractTests(unittest.TestCase):
    def test_vocabulary_gate_and_render(self):
        import tempfile
        from src.acg.capability_prompt import load_vocabulary,render
        text='@prefix skos: <http://www.w3.org/2004/02/skos/core#> .\n<https://example.org/scheme> a skos:ConceptScheme .\n'
        for i in range(15):
            text+=f'<https://example.org/c/{i}> a skos:Concept ; skos:inScheme <https://example.org/scheme> ; skos:prefLabel "Concept {i}" ; skos:definition "Test only {i}" .\n'
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'v.ttl';p.write_text(text)
            vocab=load_vocabulary(p);self.assertEqual(len(vocab['concepts']),15)
            output=render(vocab,{'resource_id':'test','description':'Test only'})
            self.assertNotIn('{{VOCABULARY_JSON}}',output)
            self.assertIn(vocab['version'],output)
            p.write_text(text.replace('skos:definition','skos:note'))
            with self.assertRaises(ValueError):load_vocabulary(p)


class ReviewRegressionTests(unittest.TestCase):
    def test_template_markers_in_vocabulary_remain_literal(self):
        from src.acg.capability_prompt import render
        vocabulary = {'version': 'v1', 'concepts': [{'definition': '{{RESOURCE_JSON}}'}]}
        resource = {'resource_id': 'r', 'description': 'Quoted "description"'}
        rendered = render(vocabulary, resource)
        payload = rendered.split('VOCABULARY_JSON:\n', 1)[1].split('\n\nRESOURCE_JSON:', 1)[0]
        self.assertEqual(json.loads(payload), vocabulary)

    def test_malformed_status_has_consistent_validation_error(self):
        from src.acg.capability_prompt import validate_response
        resource = {'resource_id': 'r', 'description': 'text'}
        vocabulary = {'version': 'v1', 'concepts': []}
        response = {'resource_id': 'r', 'vocabulary_version': 'v1', 'status': [],
                    'assignments': [], 'suggestions': [], 'reason': 'test'}
        with self.assertRaises(ValueError):
            validate_response(response, vocabulary, resource)

    def test_hash_validation_rejects_modified_text(self):
        from src.acg.ingestion.gitskills.parser import parse_content
        content = '---\nname: sample\ndescription: Example\n---\nText'
        sha = blob(content)
        self.assertEqual(parse_content(content, sha, True)[0], 'parsed')
        self.assertEqual(parse_content(content + '\n', sha, True)[0], 'hash_mismatch')
        self.assertEqual(parse_content(content.replace('\n', '\r\n'), sha, True)[0], 'hash_mismatch')

    def test_projection_queries_exclude_tools_and_untyped_resources(self):
        for number, predicate in [(11, Namespace('https://schema.org/').license),
                                  (15, A.allowedTool), (16, A.compatibility)]:
            g = Graph().parse(ROOT / 'tests/fixtures/nov26/query_fixture.ttl')
            for entity in [E.one, E.tool, E.untyped]:
                g.add((entity, predicate, Literal('recorded value')))
            query = next((ROOT / 'queries/nov26').glob(f'cq{number}_*.rq'))
            rows = list(g.query(query.read_text()))
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0].asdict()['skill'], E.one)
