const test = require('node:test'), assert = require('node:assert/strict');
const fs = require('node:fs'), ts = require('typescript'), React = require('react');
const {renderToStaticMarkup} = require('react-dom/server');
const renderer = require('react-test-renderer');
for (const extension of ['.ts', '.tsx']) require.extensions[extension] = (module, filename) => module._compile(ts.transpileModule(fs.readFileSync(filename, 'utf8'), {
  compilerOptions: {target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, esModuleInterop: true}
}).outputText, filename);
const ReleaseStatus = require('../app/predictions/PredictionReleaseStatus.tsx').default;
const InstallationStatus = require('../app/predictions/assessment/ScientificInstallationStatus.tsx').default;

test('PREDICTIONS headline keeps all three outcomes and accuracy separate without probabilities', () => {
  const html = renderToStaticMarkup(React.createElement(ReleaseStatus));
  assert.ok(html.includes('FINAL FDA PREDICTION | ACCURACY RATING'));
  for (const label of ['FDA APPROVAL', 'COMPLETE RESPONSE LETTER', 'REVIEW DELAY', 'NOT CALIBRATED', 'NOT VALIDATED']) assert.ok(html.includes(label));
  assert.equal((html.match(/>ABSTAIN</g) || []).length, 3);
  assert.equal(/\d\s*%/.test(html.replaceAll('100%', '')), false);
  const page = fs.readFileSync(require.resolve('../app/predictions/page.tsx'), 'utf8');
  assert.ok(page.indexOf('<PredictionReleaseStatus/>') < page.indexOf('<FullRosterSourceScan/>'));
  assert.ok(fs.readFileSync(require.resolve('../app/installation-audit/page.tsx'), 'utf8').includes('<ScientificInstallationStatus/>'));
});

test('task locator opens and focuses the task named by the observed currentTaskId', async () => {
  const original = {fetch: global.fetch, document: global.document, window: global.window, act: global.IS_REACT_ACT_ENVIRONMENT};
  const detailsNode = {open: false};
  const calls = [];
  let root;
  global.IS_REACT_ACT_ENVIRONMENT = true;
  global.document = {getElementById(id) {calls.push(['target', id]); return {focus(options) {calls.push(['focus', options]);}, scrollIntoView(options) {calls.push(['scroll', options]);}};}};
  global.window = {matchMedia: () => ({matches: true})};
  global.fetch = async () => Response.json({observedAt: '2026-11-08T23:50:00Z', installation: {
    state: 'OBSERVED', currentTaskId: 'medical.method-review', counts: null,
    definitions: {ACTIVE: 'Observed dependencies; work remains'},
    tasks: [
      {id: 'medical.phase-verification', title: 'Current phase review', status: 'VERIFIED', completed: 1, remaining: 0, dependency: null, evidence: 'Fixture phase ledger'},
      {id: 'medical.method-review', title: 'Method review', status: 'ACTIVE', completed: 0, remaining: 800, dependency: 'Authorized source examination', evidence: 'Fixture source ledger'},
    ],
  }});
  try {
    await renderer.act(async () => {root = renderer.create(React.createElement(InstallationStatus), {
      createNodeMock: element => element.type === 'details' ? detailsNode : null,
    });});
    const button = root.root.findByType('button');
    assert.equal(button.props.disabled, false);
    await renderer.act(async () => button.props.onClick());
    assert.equal(detailsNode.open, true);
    assert.deepEqual(calls, [
      ['target', 'medical-installation-task-medical.method-review'],
      ['focus', {preventScroll: true}], ['scroll', {behavior: 'auto', block: 'center'}],
    ]);
    const current = root.root.findAllByType('article').find(article => article.props['aria-current'] === 'step');
    assert.equal(current.props.id, 'medical-installation-task-medical.method-review');
  } finally {
    if (root) await renderer.act(async () => root.unmount());
    global.fetch = original.fetch; global.document = original.document; global.window = original.window;
    global.IS_REACT_ACT_ENVIRONMENT = original.act;
  }
});

test('missing installation observations never invent a task to locate', async () => {
  const fetchBefore = global.fetch, actBefore = global.IS_REACT_ACT_ENVIRONMENT;
  let root;
  global.IS_REACT_ACT_ENVIRONMENT = true;
  global.fetch = async () => Response.json({error: 'Sign in required'}, {status: 401});
  try {
    await renderer.act(async () => {root = renderer.create(React.createElement(InstallationStatus));});
    assert.equal(root.root.findByType('button').props.disabled, true);
    assert.equal(root.root.findAllByType('article').length, 0);
    assert.ok(root.root.findByProps({role: 'alert'}).children.join('').includes('No completion count is inferred.'));
  } finally {
    if (root) await renderer.act(async () => root.unmount());
    global.fetch = fetchBefore; global.IS_REACT_ACT_ENVIRONMENT = actBefore;
  }
});
