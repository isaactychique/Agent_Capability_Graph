"""Identity and provenance checks for the single database."""
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from acg import database


def server(sid,name='Files',repo='https://github.com/example/files',package='example-files'):
    return dict(server_id=sid,name=name,repository_url=repo,
                package_identifier=[{'registry':'npm','identifier':package}])


def tool(tid,sid,name):
    return dict(tool_id=tid,server_id=sid,name=name)


class IdentityMerge(unittest.TestCase):
    def resolve(self,servers,tools=(),skills=()):
        return database.reconcile([],servers,list(tools),list(skills),
                                  {'mcp_servers':[],'agent_skills':[]},{'server_aliases':{},'skills':[]})

    def test_duplicate_server_keeps_union_of_tools(self):
        entities,mapping,_=self.resolve([server('a'),server('b')],
                                        [tool('read','a','read'),tool('write','b','write'),tool('read-again','b','read')])
        self.assertEqual(mapping['registry','a'],mapping['registry','b'])
        self.assertEqual(mapping['registry','read'],mapping['registry','read-again'])
        tools=[e for e in entities.values() if e['kind']=='MCPTool']
        self.assertEqual({t['name'] for t in tools},{'read','write'})
        self.assertEqual({t['parent_id'] for t in tools},{mapping['registry','a']})

    def test_selected_server_inherits_tools_from_every_duplicate(self):
        curated=[{'id':'files','type':'MCPServer','parent':None,'fields':[
            {'field':'name','value':'Initial Files'},
            {'field':'repository','value':'https://github.com/example/files'}]}]
        manifest={'mcp_servers':[{'id':'files','repository':'example/files'}],'agent_skills':[]}
        entities,mapping,_=database.reconcile(curated,[server('a'),server('b')],
            [tool('one','a','read'),tool('two','b','write')],[],manifest,
            {'server_aliases':{'a':'files'},'skills':[]})
        self.assertEqual(mapping['registry','a'],mapping['registry','b'])
        self.assertEqual({e['name'] for e in entities.values() if e['kind']=='MCPTool'},{'read','write'})
        self.assertTrue(all(e['in_sample'] for e in entities.values()))

    def test_monorepo_with_different_packages_does_not_merge(self):
        entities,mapping,_=self.resolve([server('a',package='first'),server('b',package='second')])
        self.assertNotEqual(mapping['registry','a'],mapping['registry','b'])
        self.assertEqual(len(entities),2)

    def test_same_package_in_different_repositories_does_not_merge(self):
        _,mapping,_=self.resolve([server('a'),server('b',repo='https://github.com/other/fork')])
        self.assertNotEqual(mapping['registry','a'],mapping['registry','b'])

    def test_skill_merge_requires_same_repository_and_path(self):
        skills=[dict(skill_id='a',name='pdf',repository_url='https://github.com/example/skills',skill_path='skills/pdf/SKILL.md'),
                dict(skill_id='b',name='PDF renamed',repository_url='https://github.com/example/skills',skill_path='skills/pdf/SKILL.md'),
                dict(skill_id='c',name='pdf',repository_url='https://github.com/example/skills',skill_path='other/pdf/SKILL.md')]
        entities,mapping,_=self.resolve([],skills=skills)
        self.assertEqual(mapping['registry','a'],mapping['registry','b'])
        self.assertNotEqual(mapping['registry','a'],mapping['registry','c'])
        self.assertEqual(len(entities),2)


class CanonicalDatabase(unittest.TestCase):
    def test_foreign_keys_and_sample_scope(self):
        with database.connect() as db:
            self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0],'ok')
            self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(),[])
            counts=dict(db.execute('SELECT kind,COUNT(*) FROM sample GROUP BY kind'))
            self.assertEqual(counts,{'MCPServer':10,'MCPTool':55,'AgentSkill':110})
            self.assertEqual(db.execute("SELECT COUNT(*) FROM tools t JOIN entity p ON t.parent_id=p.canonical_id WHERE p.kind!='MCPServer'").fetchone()[0],0)

    def test_both_sources_and_conflicting_descriptions_are_preserved(self):
        with database.connect() as db:
            rows=db.execute("SELECT origin,payload_json FROM source_record WHERE canonical_id=?",(str(database.entity_uri('brave-search')),)).fetchall()
            self.assertEqual({o for o,_ in rows},{'curated','registry'})
            descriptions=[json.loads(v) for (v,) in db.execute("SELECT value_json FROM observation WHERE canonical_id=? AND field='description'",(str(database.entity_uri('brave-search')),))]
            self.assertGreaterEqual(len(set(descriptions)),2)
            for _,payload in rows:self.assertTrue(json.loads(payload))

    def test_graph_inputs_can_be_read_without_source_files(self):
        with patch.object(database,'CURATED_IMPORT',Path('/does/not/exist')),patch.object(database,'NORMALIZED',Path('/does/not/exist')):
            inputs=database.load_graph_inputs()
        self.assertEqual(len(inputs['curated']),63)
        self.assertEqual(len(inputs['tools']),17)
        self.assertEqual(len(inputs['skills']),107)
        self.assertEqual(len(inputs['all_skills']),272)

    def test_each_source_record_is_linked_to_canonical_entity_and_observations(self):
        with database.connect() as db:
            orphan=db.execute('SELECT COUNT(*) FROM source_record s LEFT JOIN observation o ON o.record_id=s.id WHERE o.id IS NULL').fetchone()[0]
            self.assertEqual(orphan,0)
            for (payload,) in db.execute('SELECT payload_json FROM source_record LIMIT 10'):
                self.assertIsInstance(json.loads(payload),dict)


if __name__=='__main__':unittest.main()
