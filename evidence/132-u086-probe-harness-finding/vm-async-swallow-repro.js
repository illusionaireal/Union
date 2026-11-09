const vm = require('node:vm');
const block = "const adoptedAfter = (entry.results || []).find(r => r.status === 'adopted');\n" +
  "check('x', Boolean(adoptedAfter) && entry.delivered_result_id === adoptedAfter.id);";
const names = [];
try {
  vm.runInNewContext('(async () => {' + block + '\n})()',
    { entry: { results: [{ id: 'other-result', status: 'adopted' }], delivered_result_id: undefined },
      check: (n, v) => { if (!v) throw new Error('rejected'); names.push(n); } },
    { timeout: 1000 });
  console.log('completed without throw');
} catch (e) {
  console.log('threw:', e.constructor.name, '-', String(e.message).slice(0, 80));
}
