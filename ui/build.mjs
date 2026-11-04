import {build} from 'esbuild';
import {readFile,writeFile} from 'node:fs/promises';
await build({entryPoints:['src/browser.mjs'],bundle:true,format:'esm',outfile:'../warp_relay/web/workbench.js',target:'es2022',minify:true,legalComments:'linked'});
await writeFile('../warp_relay/web/style.css',(await readFile('src/workbench.css','utf8'))+'\n'+(await readFile('src/workbench-light.css','utf8'))+'\n'+(await readFile('src/kernel-workspace.css','utf8'))+'\n'+(await readFile('src/run-workspace.css','utf8')));
