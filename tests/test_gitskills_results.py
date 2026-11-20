"""Check the committed full-dataset summaries without downloading source data."""
import csv
import json
from collections import Counter
from pathlib import Path
import unittest

def rows(path):
    with path.open(encoding="utf-8") as stream:
        return list(csv.DictReader(stream))

class Results(unittest.TestCase):
    def test_global_totals_reconcile(self):
        folder = Path(__file__).resolve().parents[1] / 'reports/gitskills'
        metrics=json.loads((folder/'run_manifest.json').read_text())['computed_metrics']
        sums=Counter()
        for row in rows(folder/'field_stats.csv'):
            key=(row['unit'],row['field'],int(row['denominator']))
            sums[key]+=int(row['records'])
        self.assertEqual(len(sums),6)
        for (_,_,denominator),count in sums.items():self.assertEqual(count,denominator)
        for name,column,expected in [
            ('parse_status.csv','unique_contents',metrics['unique_contents']),
            ('repository_license_states.csv','repositories',metrics['repositories_table']),
            ('license_coverage.csv','occurrences',metrics['occurrences']),
            ('locations.csv','occurrences',metrics['occurrences'])]:
            self.assertEqual(sum(int(row[column]) for row in rows(folder/name)),expected,name)
        conflicts=rows(folder/'name_conflicts.csv')
        self.assertEqual(len(conflicts),metrics['names_with_different_contents'])
        self.assertTrue(all(int(r['distinct_contents'])>1 for r in conflicts))
        self.assertEqual(sum(int(r['distinct_contents']) for r in conflicts),
                         metrics['named_contents_in_conflicts'])

if __name__ == "__main__":
    unittest.main()
