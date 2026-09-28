import unittest
from scripts.generate_seo_strategy import validate


class PlanContract(unittest.TestCase):
    def test_complete_owned_headings_and_publisher_frame(self):
        rows={i: {'id':i, 'keyword':f'term {i}', 'avg_monthly_searches':i,
                  'kd_proxy':20, 'funnel':'MOFU', 'ai_overview_prone':False}
              for i in range(1,15)}
        context='Remote agency. ' * 30 + 'Based in Pakistan; no Queens office.'
        raw={'mode4_cluster':{'main_topic':'Guide','source_context':context,
             'central_entity':'Local SEO','clusters':[
                 {'cluster_name':'A','primary_keyword_id':1,'keyword_ids':list(range(1,13)),
                  'h2_outline':[{'h2':'First','keyword_ids':[str(i) for i in range(1,13)]+[14, None, 'bad',1]},
                                {'h2':'Second','keyword_ids':[1,14]}]},
                 {'cluster_name':'B','primary_keyword_id':14,'keyword_ids':[14],
                  'h2_outline':[{'h2':'Other','keyword_ids':[1,14]}]}]}}
        m4,*_=validate(raw,rows)
        self.assertEqual(m4['source_context'],context)
        a=next(c for c in m4['clusters'] if c['cluster_name']=='A')
        b=next(c for c in m4['clusters'] if c['cluster_name']=='B')
        self.assertEqual(a['h2_outline'][0]['keywords'],[f'term {i}' for i in range(1,13)])
        self.assertEqual(a['h2_outline'][1]['keywords'],[])
        self.assertEqual(b['h2_outline'][0]['keywords'],['term 14'])

    def test_old_empty_plan_still_works(self):
        m4,*_=validate({}, {})
        self.assertEqual(m4['clusters'],[])
        self.assertEqual(m4['source_context'],'')


if __name__=='__main__':
    unittest.main()
