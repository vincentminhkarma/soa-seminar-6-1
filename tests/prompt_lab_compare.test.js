const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const html = fs.readFileSync(require('node:path').join(__dirname, '../app/static/ui.html'), 'utf8');
const match = html.match(/function promptComparison\([\s\S]*?\n    }/);
assert.ok(match, 'ui.html must define promptComparison');
const promptComparison = vm.runInNewContext(`(${match[0]})`, { DEFAULT_SYSTEM: 'default', JSON });
const context = { raw_text: 'Deluxe request', model: 'model-a', history: [] };
const run = (id, prompt = 'variant', overrides = {}, changed = false, failed = false) => ({ id, context: { ...context, ...overrides }, prompt, ok: !failed, category: failed ? 'upstream' : undefined, result: failed ? undefined : { status: 'OK', booking: { room_type: changed ? 'SUITE' : 'DELUXE', check_in: '2026-10-25', check_out: '2026-10-26' } } });
const baseline = (id, overrides = {}, failed = false) => run(id, 'default', overrides, false, failed);

assert.equal(promptComparison([run('variant')], 0), null, 'no baseline means no comparison');
assert.equal(promptComparison([run('variant')], 0), null, 'no baseline means no comparison');
assert.equal(promptComparison([baseline('input-mismatch', { raw_text: 'other' }), run('current')], 1), null, 'different input does not match');
assert.equal(promptComparison([baseline('same-model', { model: 'model-b' }), run('variant')], 1), null, 'different model does not match');
assert.equal(promptComparison([baseline('same-history', { history: [{ role: 'user', content: 'prior' }] }), run('variant')], 1), null, 'different history does not match');
assert.equal(promptComparison([run('baseline', 'variant'), run('variant')], 1), null, 'non-default prompt is not a baseline');
assert.equal(promptComparison([baseline('baseline')], 0), null, 'a run never compares against itself');
assert.equal(promptComparison([baseline('baseline'), run('variant')], 1).changed, false, 'unchanged result is reported as unchanged');
assert.equal(promptComparison([baseline('baseline'), run('variant', 'variant', {}, true)], 1).changed, true, 'changed result is highlighted');
assert.equal(promptComparison([baseline('baseline', {}, true), run('variant')], 1).baseline.id, 'baseline', 'failed baseline is a valid observation');
assert.equal(promptComparison([baseline('unrelated', { raw_text: 'other' }), baseline('matched'), run('variant')], 2).baseline.id, 'matched', 'latest matching baseline is selected');
console.log('Prompt Lab comparison checks passed');
