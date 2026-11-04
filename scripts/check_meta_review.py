"""Inspect the actual imported response in the local product; no API call."""
import argparse,json
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
ap=argparse.ArgumentParser()
ap.add_argument('--base-url',default='http://127.0.0.1:8876')
ap.add_argument('--browser',help='Explicit existing Chromium executable; nothing is installed')
ap.add_argument('--out',type=Path,default=Path('evidence/round23-meta/browser'))
args=ap.parse_args();OUT=args.out;OUT.mkdir(parents=True,exist_ok=True)
errors=[];posts=[]
with sync_playwright() as p:
 b=p.chromium.launch(headless=True,**({'executable_path':args.browser} if args.browser else {}));page=b.new_page(viewport={'width':1536,'height':1000});page.on('pageerror',lambda e:errors.append(str(e)));page.on('request',lambda r:posts.append(r.url) if r.method=='POST' else None)
 page.goto(args.base_url.rstrip('/')+'/#case/tma');expect(page.locator('#case-code')).to_have_attribute('data-ready','true');page.locator('[data-case-tab=review]').click()
 expect(page.locator('.review-receipt')).to_contain_text('muse-spark-1.3');expect(page.locator('.review-receipt')).to_contain_text('24.525s')
 expect(page.locator('[data-model-stage=packet]')).to_have_attribute('aria-pressed','true');expect(page.locator('.model-stage-detail')).to_contain_text('2 recorded writes');expect(page.locator('.model-stage-detail')).to_contain_text('49152');expect(page.locator('[data-acquired-line]')).to_have_count(0)
 page.locator('[data-model-stage=source]').click();expect(page.locator('[data-acquired-line]')).to_have_count(4);expect(page.locator('.model-stage-detail')).to_contain_text('290');expect(page.locator('.model-stage-detail')).to_contain_text('124 real source lines')
 for line in [348,402,510,613,402]:
  page.locator(f'[data-acquired-line="{line}"]').click();expect(page.locator('#case-code')).to_have_attribute('data-focused-line',str(line));expect(page.locator('#source-mapping')).to_contain_text('not an exact access')
 page.screenshot(path=str(OUT/'01-meta-source.png'))
 page.locator('[data-model-stage=response]').click();expect(page.locator('.model-stage-detail')).to_contain_text('9,587');expect(page.locator('.model-stage-detail')).to_contain_text('Resolve which debug-region start');expect(page.locator('.response-identity')).to_contain_text('chatcmpl-01a1a273');page.screenshot(path=str(OUT/'02-response-receipt.png'))
 saved=json.loads((Path(__file__).resolve().parents[1]/'warp_relay/reviews/tma-0.json').read_text())
 expect(page.locator('.stage-finding small')).to_contain_text('Saved hypothesis')
 expect(page.locator('.stage-finding p')).to_have_text(saved['model']['diagnosis']['findings'][1]['claim'])
 page.locator('[data-model-stage=checks]').click();expect(page.locator('.model-stage-detail')).to_contain_text('No measured win');page.screenshot(path=str(OUT/'03-integrity-limits.png'))
 page.locator('[data-review-provider=baseline]').click();expect(page.locator('#case-review')).to_contain_text('Deterministic diagnostic baseline');expect(page.locator('.review-metrics')).to_contain_text('2/2')
 page.locator('[data-review-provider=model]').click();expect(page.locator('#case-review')).to_contain_text('Recorded Meta response');page.locator('[data-model-stage=source]').click()
 page.set_viewport_size({'width':390,'height':844});page.screenshot(path=str(OUT/'04-mobile-model.png'),full_page=True);assert page.evaluate('document.documentElement.scrollWidth<=innerWidth');assert 'retained' not in page.locator('#mobile-version').inner_text();assert page.locator('.case-evidence').evaluate('(e)=>e.scrollWidth<=e.clientWidth')
 page.locator('[data-acquired-line="402"]').click();expect(page.locator('#case-code')).to_have_attribute('data-focused-line','402');expect(page.locator('.case-source-panel')).to_be_visible();page.screenshot(path=str(OUT/'05-mobile-source.png'),full_page=True)
 assert not errors and not posts,(errors,posts)
 b.close()
(OUT/'check.json').write_text(json.dumps({'model':'muse-spark-1.3','actual_recorded_calls':1,'browser_model_calls':0,'post_requests':posts,'errors':errors,'regions':[348,402,510,613],'desktop':True,'mobile_width':390,'baseline_comparison':'same 2/2 coverage, no measured superiority'},indent=2))
print('Actual recorded Meta response, receipt, baseline and four region navigation: passed; no POST requests')
