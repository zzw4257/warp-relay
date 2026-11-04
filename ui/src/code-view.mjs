import {FileDiff,File,registerCustomLanguage,registerCustomTheme,preloadHighlighter} from '@pierre/diffs';
import {annotations,barrierAnnotations,candidateModel} from './model.mjs';
// Syntax color identifies instruction classes; red is reserved for a decision or deletion.
registerCustomTheme('warp-light',async()=>({name:'warp-light',type:'light',
  colors:{'editor.background':'#ffffff','editor.foreground':'#27313b','editorLineNumber.foreground':'#77838d'},
  tokenColors:[
    {scope:'comment',settings:{foreground:'#697782'}},
    {scope:['keyword','storage'],settings:{foreground:'#68517e'}},
    {scope:'constant.numeric',settings:{foreground:'#285e80'}},
    {scope:'variable',settings:{foreground:'#27313b'}}
  ]
}));
registerCustomLanguage('warp-ptx',async()=>({default:[{name:'warp-ptx',scopeName:'source.warp-ptx',patterns:[
  {name:'comment.line.double-slash',match:'//.*$'},
  {name:'variable.other',match:'%[a-zA-Z][a-zA-Z0-9_]*'},
  {name:'keyword.control',match:'\\b(?:bar|st|ld|mov|add|sub|mul|mad|fma|setp|bra|ret|shfl|cvt|cvta|and|or|shl|shr|selp|div|sqrt|rsqrt|atom|red)(?:\\.[a-zA-Z0-9_]+)*\\b'},
  {name:'constant.numeric',match:'\\b(?:0[xX][0-9a-fA-F]+|0[fFdD][0-9a-fA-F]+|[0-9]+(?:\\.[0-9]+)?)\\b'},
  {name:'storage.type',match:'\\.(?:entry|reg|param|shared|global|local|visible|version|target|address_size|b[0-9]+|u[0-9]+|s[0-9]+|f[0-9]+|pred)\\b'}
]}]}),['ptx']);
let prepared;
export function prepareCode(){return prepared ||= preloadHighlighter({themes:['warp-light'],langs:['warp-ptx'],preferredHighlighter:'shiki-js'});}
const css=`:host{--diffs-font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;--diffs-font-size:var(--warp-code-size,14px);--diffs-line-height:24px;--diffs-bg:#ffffff;--diffs-fg:#27313b;--diffs-bg-deletion:#fff0ec;--diffs-bg-addition:#edf6ed;} [data-line]{min-height:24px;} [data-warp-focused]{background:#e8f0f1!important;font-weight:600;line-height:24px!important;opacity:1!important;} [data-line-type="change-deletion"][data-warp-focused]{background:#ffe9e2!important;} [data-line-type="change-addition"][data-warp-focused]{background:#e5f2e7!important;} [data-warp-gutter]{color:#315d64!important;background:#e8f0f1!important;} pre{background:#fff!important;} [data-line-annotation]{font-family:inherit;} [data-line-number-content]{white-space:pre;} `;
export async function mountCode(host,data,state={}) {
  await prepareCode();
  if(!host.isConnected) return {cleanUp(){},focus(){}};
  const m=candidateModel(data,state.index??0);if(!m)return {cleanUp(){},focus(){}};
  const diff=state.tab!=='code'&&m.index>0;
  const styleNote=(node,active)=>{
    node.dataset.emphasized=String(active);
    node.querySelector('[data-note-focus]')?.setAttribute('aria-pressed',String(active));
    node.style.color=active?'#315d64':'#65717b';
    node.style.borderLeftColor='transparent';
  };
  const createNote=({metadata:a})=>{
    const node=document.createElement('div');node.className='inline-access';node.dataset.access=a.id;
    node.style.cssText='height:28px;box-sizing:border-box;padding:3px 12px;white-space:nowrap;background:#f3f6f7;';
    const button=document.createElement('button');button.type='button';button.dataset.noteFocus=a.id;
    button.style.cssText='padding:0;margin:0;border:0;border-radius:0;background:none;color:inherit;text-align:left;cursor:pointer;font:12px/21px ui-monospace,monospace;';
    button.setAttribute('aria-label',`Inspect ${a.mode} at candidate line ${a.line}`);
    button.onclick=()=>document.querySelector(`button.access[data-access="${a.id}"]`)?.click();
    button.textContent=`${a.tag} / ${a.mode.toUpperCase()} · actor ${a.actor} · shared ${m.range??'unknown'}`;
    node.append(button);styleNote(node,false);return node;
  };
  let done;
  const rendered=new Promise(resolve=>done=resolve);
  const viewer=new (diff?FileDiff:File)({theme:'warp-light',themeType:'light',preferredHighlighter:'shiki-js',disableFileHeader:true,diffStyle:'unified',lineDiffType:'none',expandUnchanged:false,collapsedContextThreshold:12,parseDiffOptions:{context:12},overflow:'scroll',hunkSeparators:'line-info-basic',unsafeCSS:css,renderAnnotation:createNote,onPostRender:(node,_instance,phase)=>{if(phase==='unmount')return;
      if(diff){const shadow=node.shadowRoot;for(const gutter of shadow?.querySelectorAll('[data-column-number][data-line-index]')||[]){
        const line=shadow.querySelector('[data-line][data-line-index="'+gutter.dataset.lineIndex+'"]');
        if(!line)continue;const type=line.dataset.lineType;
        const old=type==='change-addition'?'—':line.dataset.altLine||line.dataset.line;
        const next=type==='change-deletion'?'—':line.dataset.line;
        const number=gutter.querySelector('[data-line-number-content]');if(number)number.textContent=old.padStart(3)+'  '+next.padStart(3);
        gutter.dataset.originalLine=old;gutter.dataset.candidateLine=next;
      }}done();}});
  const file={name:'kernel.ptx',contents:m.row.source,lang:'warp-ptx'};
  viewer.render({containerWrapper:host,...(diff?{oldFile:{name:'kernel.ptx',contents:m.original.source,lang:'warp-ptx'},newFile:file}:{file}),lineAnnotations:annotations(m,diff)});
  await rendered;
  function focus(key) {
    const access=m.accesses.find(a=>a.key===key)||m.accesses[0];
    host.querySelectorAll('.inline-access').forEach(n=>n.style.fontWeight=n.dataset.access===key?'700':'400');
    if(!access){
      const line=Math.max(1,m.row.source.split('\n').findIndex(s=>/bar\.sync/.test(s))+1);
      const target=host.querySelector('diffs-container')?.shadowRoot?.querySelector('[data-line="'+line+'"]');
      if(target){const rect=host.getBoundingClientRect();host.scrollTop+=(target.getBoundingClientRect().top-rect.top)/(rect.height/host.clientHeight||1)-150;}
      return;
    }
    // Annotation coordinates belong to the file, never the visible row index.
    const marker=host.querySelector(`[data-access="${access.key}"]`);
    if(marker){const box=marker.getBoundingClientRect(),container=host.getBoundingClientRect();host.scrollTop+=(box.top-container.top)/(container.height/host.clientHeight||1)-125;}
  }
  function selectFocus(key){
    const access=m.accesses.find(a=>a.key===key);
    const shadow=host.querySelector('diffs-container')?.shadowRoot;
    shadow?.querySelectorAll('[data-warp-focused]').forEach(n=>n.removeAttribute('data-warp-focused'));
    shadow?.querySelectorAll('[data-warp-gutter]').forEach(n=>n.removeAttribute('data-warp-gutter'));
    const line=key==='barrier'?shadow?.querySelector('[data-line][data-line-type="change-deletion"]'):key==='insertion'?shadow?.querySelector('[data-line][data-line-type="change-addition"]'):access?shadow?.querySelector('[data-line="'+access.line+'"]:not([data-line-type="change-deletion"])'):null;
    if(line){line.setAttribute('data-warp-focused',key);host.dataset.focusedLine=key==='barrier'?String(barrierAnnotations(m,diff)[0].lineNumber):String(access?.line??line.dataset.line);host.dataset.focusedSide=key==='barrier'?'original':'candidate';const gutter=shadow.querySelector('[data-column-number][data-line-index="'+line.dataset.lineIndex+'"]');gutter?.setAttribute('data-warp-gutter','');}
    host.querySelectorAll('.inline-access').forEach(n=>styleNote(n,n.dataset.access===key));
    host.querySelectorAll('.inline-change').forEach(n=>styleNote(n,key==='barrier'));
    const node=host.querySelector(`[data-access="${key}"]`);if(node){const r=node.getBoundingClientRect(),h=host.getBoundingClientRect();if(r.top<h.top||r.bottom>h.bottom)focus(key);}
  }
  focus('first');
  if(barrierAnnotations(m,diff).length)selectFocus('barrier');
  else if(diff&&!m.accesses.length){const added=host.querySelector('diffs-container')?.shadowRoot?.querySelector('[data-line][data-line-type="change-addition"]');if(added&&/^\s*bar\.sync\s+\d+\s*;\s*$/.test(added.textContent))selectFocus('insertion');}
  host.dataset.ready='true';
  return {cleanUp:()=>viewer.cleanUp(),focus:selectFocus};
}

// Library viewer accepts only verified PTX row coordinates, including explicit debug maps.
export async function mountCaseSource(host,source,onLine=()=>{},options={}){
 await prepareCode();if(!host.isConnected)return{cleanUp(){},focus(){}};
 let ready;const rendered=new Promise(r=>ready=r);const isDiff=options.originalSource!==undefined;const viewer=new (isDiff?FileDiff:File)({theme:'warp-light',themeType:'light',preferredHighlighter:'shiki-js',disableFileHeader:true,diffStyle:'unified',lineDiffType:'none',expandUnchanged:false,parseDiffOptions:{context:14},collapsedContextThreshold:14,overflow:'scroll',unsafeCSS:css,onPostRender:(_n,_v,phase)=>{if(phase!=='unmount')ready();}});
 const file={name:'kernel.ptx',contents:source,lang:'warp-ptx'};viewer.render({containerWrapper:host,...(isDiff?{oldFile:{name:'kernel.ptx',contents:options.originalSource,lang:'warp-ptx'},newFile:file}:{file})});await rendered;host.dataset.ready='true';host.dataset.view=isDiff?'changes':'source';
 const click=e=>{const row=e.composedPath().find(n=>n?.dataset?.line);if(row&&row.dataset.lineType!=='change-deletion')onLine(Number(row.dataset.line));};host.addEventListener('click',click);
 return {cleanUp(){host.removeEventListener('click',click);viewer.cleanUp();},focus(lines){const shadow=host.querySelector('diffs-container')?.shadowRoot;shadow?.querySelectorAll('[data-warp-focused]').forEach(n=>n.removeAttribute('data-warp-focused'));for(const line of lines)shadow?.querySelector(`[data-line="${line}"]:not([data-line-type="change-deletion"])`)?.setAttribute('data-warp-focused','case');const row=shadow?.querySelector(`[data-line="${lines[0]}"]:not([data-line-type="change-deletion"])`);if(row){const a=row.getBoundingClientRect(),b=host.getBoundingClientRect();if(a.top<b.top||a.bottom>b.bottom)host.scrollTop+=(a.top-b.top)/(b.height/host.clientHeight||1)-120;}host.dataset.focusedLine=String(lines[0]??'');}};
}
