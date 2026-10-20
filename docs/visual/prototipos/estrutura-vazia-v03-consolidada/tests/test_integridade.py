"""Laboratório de leitura — Playwright/Chromium.

    python -m pip install playwright
    python -m playwright install chromium
    python tests/test_integridade.py

For tests in an environment with system Chromium only:
    CHROMIUM_EXECUTABLE=/usr/bin/chromium python tests/test_integridade.py

Tests are offline, avoid file://, and separate unique faces from face visits.
"""
from collections import Counter
from pathlib import Path
import json
import os
import re
from playwright.sync_api import sync_playwright

HTML = (Path(__file__).resolve().parent.parent / 'index.html').read_text(encoding='utf-8')
ARTIFACT = Path(__file__).resolve().parent.parent / 'resultado-testes.json'
REPORTS=[]

def normal(s):
    return re.sub(r'\s+', ' ', s).strip()

def assert_ok(cond, msg):
    if not cond: raise AssertionError(msg)

def setup(browser, width, height):
    page=browser.new_page(viewport={'width':width,'height':height}, reduced_motion='reduce')
    errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.set_content(HTML,wait_until='load')  # offline; localStorage unavailable in this injected context
    assert_ok(not errors,errors)
    return page,errors

def update(page, *, font=None, spacing=None, long=None, ad=None):
    if font is not None:
        page.locator('#fontRange').evaluate('(el,value)=>{el.value=String(value);el.dispatchEvent(new Event("input",{bubbles:true}));}',font)
        page.wait_for_timeout(260)
    if spacing is not None:
        page.locator('#spacing').evaluate('(el,value)=>{el.value=String(value);el.dispatchEvent(new Event("change",{bubbles:true}));}', spacing)
    if long is not None:
        page.locator('#longText').evaluate('(el,yes)=>{el.checked=yes;el.dispatchEvent(new Event("change",{bubbles:true}));}',long)
    if ad is not None:
        page.locator('#adPreview').evaluate('(el,yes)=>{el.checked=yes;el.dispatchEvent(new Event("change",{bubbles:true}));}',ad)

def validate_full_flip(page,errors,*, label=''):
    generated=page.evaluate('window.__rgLabAudit()')
    expected=[p['key'] for p in generated]
    assert_ok(len(expected)==len(set(expected)),f'Duplicated keys in buildPages: {label}')
    visits=[]; sequences=[]; occluded=[]; horizontal=[]; ids_to_text={}
    for step in range(170):
        capture=page.evaluate('''() => {
            const shown=[...document.querySelectorAll('#flipStage > .page')];
            return {
              keys:shown.map(p=>p.dataset.key),
              dataPages:shown.map(p=>Number(p.dataset.page)),
              texts:shown.flatMap(p=>[...p.querySelectorAll('.flow-block[data-anchor]')].map(b=>({id:b.dataset.anchor,text:b.textContent}))),
              occluded:shown.flatMap(p=>[...p.querySelectorAll('.story-body')].filter(b=>b.scrollHeight>b.clientHeight+2 && getComputedStyle(b).overflowY!=='auto').map(b=>({page:p.dataset.key,extra:b.scrollHeight-b.clientHeight,overflow:getComputedStyle(b).overflowY}))),
              overflow:Math.max(document.documentElement.scrollWidth,document.body.scrollWidth)-window.innerWidth,
              disabled:document.querySelector('#nextBtn').disabled
            };
        }''')
        visits+=capture['keys']
        sequences.append(capture['keys'])
        occluded+=capture['occluded']
        if capture['overflow']>2:horizontal.append((capture['keys'],capture['overflow']))
        for item in capture['texts']:
            ids_to_text[item['id']]=item['text']
        if capture['disabled']:break
        page.locator('#nextBtn').evaluate('(el)=>el.click()')
    else:raise AssertionError('navigation did not reach backcover')
    counts=Counter(visits)
    assert_ok(not occluded,f'{label} hidden text {occluded[:5]}')
    assert_ok(not horizontal,f'{label} horizontal overflow {horizontal[:5]}')
    assert_ok(sequences[0]==['cover'],f'{label} cover {sequences[0]}')
    assert_ok(sequences[-1]==['backcover'],f'{label} backcover {sequences[-1]}')
    assert_ok(set(visits)==set(expected),f'{label} missing {set(expected)-set(visits)} extra {set(visits)-set(expected)}')
    assert_ok(all(v==1 for v in counts.values()),f'{label} repeated face: {dict((k,v) for k,v in counts.items() if v!=1)}')
    assert_ok(not errors,f'{label} js errors {errors}')
    page.locator('#modeScroll').click()
    assert_ok(page.locator('#scrollRoot').is_visible(),f'{label} scroll not visible')
    scrollIds=page.evaluate('''() => [...document.querySelectorAll('#scrollRoot .story-continuous .flow-block[data-anchor]')].map(b=>({id:b.dataset.anchor,text:b.textContent}))''')
    assert_ok(normal(' '.join(ids_to_text.values()))==normal(' '.join(x['text'] for x in scrollIds)),f'{label} lost story text')
    page.locator('#modeFlip').click()
    return {'case':label,'total_logical_faces':len(expected), 'unique_faces':len(counts),
            'face_visits':len(visits),'visited_sequence':sequences,'first':sequences[0],
            'last':sequences[-1], 'hidden_story_blocks':len(occluded),
            'horizontal_overflow_events':len(horizontal),'story_text_matches_continuous':True,
            'js_errors':len(errors)}

def test_resize(browser):
    page,errors=setup(browser,390,844)
    details=page.locator('#settingsShell')
    assert_ok(not details.evaluate('(e)=>e.open'),'Mobile should start folded')
    page.set_viewport_size({'width':1024,'height':768});page.wait_for_timeout(350)
    assert_ok(details.evaluate('(e)=>e.open'),'390→1024 must show settings')
    page.set_viewport_size({'width':390,'height':844});page.wait_for_timeout(350)
    assert_ok(not details.evaluate('(e)=>e.open'),'1024→390 must restore folded mobile default')
    page.locator('#settingsShell > summary').click()
    assert_ok(details.evaluate('(e)=>e.open'),'Mobile user must open settings')
    page.set_viewport_size({'width':1024,'height':768});page.wait_for_timeout(350)
    assert_ok(details.evaluate('(e)=>e.open'),'Mobile-open→desktop')
    page.set_viewport_size({'width':390,'height':844});page.wait_for_timeout(350)
    assert_ok(details.evaluate('(e)=>e.open'),'Explicit mobile-open should persist')
    page.locator('#settingsShell > summary').click()
    assert_ok(not details.evaluate('(e)=>e.open'),'Mobile can close settings')
    page.set_viewport_size({'width':1024,'height':768});page.wait_for_timeout(350)
    assert_ok(details.evaluate('(e)=>e.open'),'Desktop must open after manually closed mobile')
    page.set_viewport_size({'width':390,'height':844});page.wait_for_timeout(350)
    assert_ok(not details.evaluate('(e)=>e.open'),'Manual mobile-close should persist')
    # reverse journey: starts desktop, crosses breakpoint both directions
    page2,errors2=setup(browser,1024,768)
    panel=page2.locator('#settingsShell')
    assert_ok(panel.evaluate('(e)=>e.open'),'Desktop must start open')
    page2.set_viewport_size({'width':390,'height':844});page2.wait_for_timeout(350)
    assert_ok(not panel.evaluate('(e)=>e.open'),'1024→390 should fold if no mobile choice')
    page2.set_viewport_size({'width':1024,'height':768});page2.wait_for_timeout(350)
    assert_ok(panel.evaluate('(e)=>e.open'),'390→1024 must be visible')
    # ensure reader choices persist during width change
    update(page2, font=130)
    page2.locator('#modeScroll').click()
    page2.set_viewport_size({'width':390,'height':844});page2.wait_for_timeout(350)
    assert_ok(page2.locator('#modeScroll').get_attribute('aria-pressed')=='true','Mode preference lost')
    assert_ok(page2.locator('#fontOut').text_content()=='130%','Font preference lost')
    assert_ok(not errors and not errors2,f'JS error {errors},{errors2}')
    page.close();page2.close()
    return {'case':'breakpoint 390→1024→390 and 1024→390→1024','mobile_manual_open_close_preserved':True,'desktop_settings_always_available':True,'reader_mode_and_typography_preserved':True,'js_errors':0}

def test_dialogue(browser):
    page,errors=setup(browser,390,844)
    page.locator('#tocBtn').click()
    assert_ok(page.locator('#drawer').evaluate("x=>x.classList.contains('open')"),'sumario not open')
    page.keyboard.press('Shift+Tab')
    name=page.evaluate('document.activeElement.id')
    assert_ok(name!='','Dialog focus left to body')
    page.keyboard.press('Escape')
    assert_ok(page.evaluate('document.activeElement.id')=='tocBtn','focus not restored')
    assert_ok(not errors,errors)
    page.close()
    return {'case':'dialogue','esc_focus_restore':True,'js_errors':0}

def test_oversize(browser):
    page, errors = setup(browser, 1024, 768)
    # Figuras+legendas e tabelas são componentes indivisíveis, maiores que uma face.
    page.add_style_tag(content='''.flow-fig .slot{min-height:950px!important;height:950px!important} .flow-table{min-height:870px!important}''')
    update(page, long=True, font=150)
    seen = set()
    for _ in range(170):
        regions = page.locator('#flipStage .needs-scroll .story-body')
        for i in range(regions.count()):
            el = regions.nth(i)
            info = el.evaluate('''e => ({scroll:e.scrollHeight, client:e.clientHeight, tab:e.tabIndex, overflow:getComputedStyle(e).overflowY, hasFigure:!!e.querySelector('.flow-fig'), hasTable:!!e.querySelector('.flow-table')})''')
            for kind, present in [('figure',info['hasFigure']),('table',info['hasTable'])]:
                if not present or kind in seen: continue
                assert_ok(info['scroll']>info['client']+10, f'{kind} is not overflowed')
                assert_ok(info['tab']==0, f'{kind} is not keyboard-focusable')
                assert_ok(info['overflow']=='auto', f'{kind} lacks accessible scrolling')
                el.focus()
                page.keyboard.press('PageDown')
                page.wait_for_timeout(75)
                assert_ok(el.evaluate('e => e.scrollTop')>0, f'{kind} cannot scroll with keyboard')
                seen.add(kind)
        if seen=={'figure','table'} or page.locator('#nextBtn').is_disabled():break
        page.locator('#nextBtn').evaluate('(el)=>el.click()')
    assert_ok(seen=={'figure','table'},f'Not both oversized components examined: {seen}')
    assert_ok(not errors, errors)
    page.close()
    return {'case':'oversized-figure-and-table','tested_components':sorted(seen), 'focusable_region':True,'keyboard_page_down_scrolls':True,'js_errors':0}

def test_ads(browser):
    page,errors=setup(browser,1440,960)
    base=page.evaluate("window.__rgLabAudit().map(x=>x.kind)")
    assert_ok('ad' not in base,'Advertisement should not occupy default face')
    update(page,ad=True)
    sponsored=page.evaluate("window.__rgLabAudit().map(x=>x.kind)")
    assert_ok('ad' in sponsored,'Preview advertisement not added')
    update(page,ad=False)
    again=page.evaluate("window.__rgLabAudit().map(x=>x.kind)")
    assert_ok('ad' not in again,'Advertisement face did not disappear')
    assert_ok(again[-1]=='backcover','Backcover lost after ad change')
    assert_ok(not errors,errors)
    page.close()
    return {'case':'conditional-ad','default_ad_faces':0,'preview_available':True,'removed_without_blank_face':True,'js_errors':0}

def main():
    chromium=os.environ.get('CHROMIUM_EXECUTABLE')
    with sync_playwright() as pw:
        b=pw.chromium.launch(executable_path=chromium,headless=True,args=['--no-sandbox'] if chromium else [])
        REPORTS.append(test_resize(b))
        print('PASS breakpoint crossing')
        REPORTS.append(test_dialogue(b))
        print('PASS dialogue')
        REPORTS.append(test_ads(b))
        print('PASS conditional ad')
        for width,height,font,spacing,long in [
            (1024,768,150,1.3,True),
            (1024,768,90,1,False),
            (390,844,150,1.3,True),
            (320,700,100,1,False),
            (1440,960,120,1.15,False),
            (800,1100,150,1,False)
        ]:
            page,errors=setup(b,width,height)
            update(page,font=font,spacing=spacing,long=long)
            label=f'{width}x{height} font={font}% spacing={spacing} long={long}'
            result=validate_full_flip(page,errors,label=label)
            REPORTS.append(result)
            print('PASS',label,'unique',result['unique_faces'],'visits',result['face_visits'])
            page.close()
        REPORTS.append(test_oversize(b))
        print('PASS oversized module')
        b.close()
    ARTIFACT.write_text(json.dumps({'status':'PASS','method':'Playwright Chromium headless / HTML offline in memory', 'cases':REPORTS},ensure_ascii=False,indent=2),encoding='utf-8')
    print('ALL PASSED',len(REPORTS), 'cases; report:',ARTIFACT)

if __name__=='__main__':main()