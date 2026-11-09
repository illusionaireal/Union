// Verified: with the fix, an assertion failure inside the async IIFE properly
// reaches the catch and is reported as accepted=false.
const vm = require('node:vm');

function runHarness(block, input, predicate) {
  return new Promise(resolve => {
    const names = [];
    const context = {
      inflight: null,
      ...input.variables,
      check: (name, value = true) => {
        if (!value) throw new Error('review assertion rejected');
        names.push(name);
      },
    };
    (async () => {
      try {
        const value = await vm.runInNewContext(
          '(async () => {' + block + '\n})()', context, { timeout: 1000 });
        resolve({ accepted: predicate ? value === true : true, checks: names.length });
      } catch (error) {
        if (error.message !== 'review assertion rejected') throw error;
        resolve({ accepted: false, checks: names.length });
      }
    })().catch(error => { resolve({ parseError: error.name }); });
  });
}

const failingBlock = `
  check('should reject', false);
`;
const passingBlock = `
  check('ok', true);
`;
const asyncFailingBlock = `
  await Promise.resolve();
  check('reject after await', false);
`;

(async () => {
  console.log('failing:', JSON.stringify(await runHarness(failingBlock, {}, false)));
  console.log('passing:', JSON.stringify(await runHarness(passingBlock, {}, false)));
  console.log('async-failing (the old bug):', JSON.stringify(await runHarness(asyncFailingBlock, {}, false)));
})();
