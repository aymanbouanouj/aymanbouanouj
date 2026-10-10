"""Offline checks for evidence-driven project cards; never assert false CI success."""
import base64,datetime as dt,json,sys,unittest
from pathlib import Path
from urllib.error import HTTPError
from xml.etree import ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from engineering import collect,render,verify,dependency_names,OWNER
class EngineeringTests(unittest.TestCase):
 def test_detection(self):
  self.assertIn('laravel/framework',dependency_names('composer.json','{"require":{"laravel/framework":"^12"}}'))
  self.assertIn('vite',dependency_names('package.json','{"devDependencies":{"vite":"^8"}}'))
 def test_no_fabricated_ci_success(self):
  names=['morocco2030','PC-Full-Check','violetgate','ayman-calc']
  def fake(url,token):
   if '/users/' in url:
    return [{'name':name,'owner':{'login':OWNER},'private':False,'fork':False,'archived':False,'disabled':False,'default_branch':'main'} for name in names]
   if '/contents/' in url:
    if not url.endswith('composer.json'):
     raise HTTPError(url,404,'not found',{},None)
    data='{"require":{"laravel/framework":"^12"}}'
    return {'type':'file','encoding':'base64','size':len(data),'content':base64.b64encode(data.encode()).decode()}
   if '/actions/runs' in url:
    return {'workflow_runs':[{'head_branch':'main','status':'completed','name':'CI','event':'push','conclusion':'failure','html_url':'https://github.com/test'}]}
   if '/releases?' in url:return [{'draft':False,'prerelease':False,'tag_name':'v1.0.0','html_url':'https://github.com/test'}]
   raise AssertionError(url)
  data=collect(get=fake,now=dt.datetime.now(dt.timezone.utc))
  verify(data,max_age_hours=2)
  self.assertEqual({x['name'] for x in data['frameworks']},{'Laravel'})
  self.assertTrue(all(x['ci']=='failure' for x in data['projects']))
  for t in ('dark','light'):
   svg=render(t,data);ET.fromstring(svg)
   self.assertIn('FAILURE',svg)
 def test_no_network_placeholder(self):
  for t in ('dark','light'):
   x=render(t);ET.fromstring(x)
   self.assertIn('AWAITING FIRST VERIFIED ENGINEERING SCAN',x)
 def test_readme(self):
  text=(ROOT/'README.md').read_text(encoding='utf-8')
  self.assertIn('engineering-dark.svg',text)
  self.assertIn('engineering-light.svg',text)
  self.assertIn('SGA-BTS/pull/1',text)
if __name__=='__main__':unittest.main()
