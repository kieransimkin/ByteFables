// DOM-contract tests, not a substitute for the separate real-browser smoke test.
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { runInNewContext } from 'node:vm';
const script = readFileSync(new URL('../integrations/web/artwork-assets/gallery.js', import.meta.url), 'utf8');
class Element {
  constructor(tag) { this.tag = tag; this.value = ''; this.children = []; this.events = {}; }
  append(...nodes) { this.children.push(...nodes); }
  replaceChildren(...nodes) { this.children = [...nodes]; }
  addEventListener(name, callback) { this.events[name] = callback; }
  set innerHTML(_) { throw new Error('Untrusted HTML insertion is forbidden'); }
}
function row(index, size = 128) {
  const digest = index.toString(16).padStart(64, '0');
  const path = `assets/sigil-neon-c4/${digest}`;
  return { digest, family: 'sigil', palette: 'neon', complexity: 4, sizes: [16, size],
    files: [...new Set([16, size])].map(s => ({format:'png', file:`${path}/${s}.png`, frames:[{size:s}]})) };
}
function run(rows) {
  const nodes = Object.fromEntries(['status','query','family','palette','size','grid','previous','next','position','filters']
    .map(id => [id, new Element(id)]));
  nodes.size.value = '128';
  runInNewContext(script, { window:{BYTEFABLES_ASSETS:rows}, document:{
    getElementById:id=>nodes[id], createElement:tag=>new Element(tag)
  }});
  return nodes;
}
test('gallery paginates 1000 entries without inserting all image DOM nodes', () => {
  const nodes = run(Array.from({length:1000},(_,i)=>row(i)));
  assert.equal(nodes.grid.children.length,48);
  assert.equal(nodes.previous.disabled,true);
  nodes.next.events.click();
  assert.equal(nodes.grid.children.length,48);
  assert.equal(nodes.position.textContent,'Page 2 of 21');
  assert.equal(nodes.previous.disabled,false);
});
test('full digest search, empty results and native-size selection use exact values', () => {
  const data=[row(1),row(2)]; const nodes=run(data);
  nodes.query.value=data[1].digest;nodes.query.events.input();
  assert.equal(nodes.grid.children.length,1);
  nodes.size.value='16';nodes.size.events.input();
  const preview=nodes.grid.children[0].children.find(n=>n.className==='preview');
  assert.equal(preview.children[0].width,16);
  assert.equal(preview.children[0].height,16);
  nodes.query.value='not-a-digest';nodes.query.events.input();
  assert.equal(nodes.grid.children.length,0);
  assert.equal(nodes.next.disabled,true);
});
test('gallery selects an available native size rather than fabricating 128px', () => {
  const nodes=run([row(5,32)]);
  assert.equal(nodes.size.value,'32');
  assert.equal(nodes.grid.children.length,1);
});
test('invalid paths are not converted into external image or download links', () => {
  for (const file of ['https://example.com/x.png','../private.png','assets/../../x.png','javascript:alert(1)']) {
    const data=row(1);data.files=data.files.map(f=>({...f,file}));
    assert.equal(run([data]).grid.children.length,0);
  }
});
test('missing or oversized inventory is rejected and script uses only text content', () => {
  assert.match(run(undefined).status.textContent,/Invalid/);
  assert.match(run(Array(8193)).status.textContent,/Invalid/);
  const data=row(1);data.family='<svg onload=alert(1)>';
  const nodes=run([data]);
  assert.equal(nodes.family.children[0].textContent,data.family);
});
