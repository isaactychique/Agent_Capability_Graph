import json
from datetime import date
import unittest
from src.acg.ingestion.gitskills.export_dataset import encode_value, field_rows, is_empty

class MetadataExportTests(unittest.TestCase):
    def test_types_and_scopes_are_preserved(self):
        rows=list(field_rows('sha', {'version':'1.0','metadata':{'version':1.0},'user-invocable':False,'tags':[]}))
        indexed={(r[1],r[2]):r for r in rows}
        self.assertEqual(indexed['top','version'][3],'string')
        self.assertEqual(indexed['metadata','version'][3],'number')
        self.assertEqual(indexed['top','user-invocable'][4],'present')
        self.assertEqual(indexed['top','tags'][4],'empty')
        self.assertEqual(json.loads(indexed['top','metadata'][6]),{'version':1.0})

    def test_dates_and_nonstring_keys_are_not_silently_coerced(self):
        encoding,text=encode_value({1:date(2026,11,26),'1':'literal'})
        self.assertEqual(encoding,'typed_json')
        obj=json.loads(text)
        self.assertEqual(obj['entries'][0][0]['type'],'number')
        self.assertEqual(obj['entries'][0][1],{'type':'date','value':'2026-11-26'})
        self.assertEqual(obj['entries'][1][0]['type'],'string')

    def test_recursive_yaml_is_explicit(self):
        v=[];v.append(v)
        encoding,text=encode_value(v)
        self.assertEqual(encoding,'typed_json')
        self.assertEqual(json.loads(text)['items'][0],{'type':'reference','id':0})

    def test_json_quotes_unicode_and_false_are_lossless(self):
        v=['中文','a\nb','"quoted"',False,0,None]
        enc,text=encode_value(v)
        self.assertEqual(enc,'json');self.assertEqual(json.loads(text),v)
        self.assertFalse(is_empty(False));self.assertFalse(is_empty(0))
        self.assertTrue(is_empty('  '));self.assertTrue(is_empty(None))
