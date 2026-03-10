import test from 'node:test';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const { classifyDestructiveAction } = require('../dist/core/DestructiveClassifier.js');

test('classify: delete 4382 emails -> catastrophic with bulk count', () => {
  const result = classifyDestructiveAction('Gmail.deleteMessages', {
    query: 'in:inbox',
    count: 4382,
  }, {
    moduleName: 'Gmail',
    methodName: 'deleteMessages',
    bulkThreshold: 20,
  });

  assert.equal(result.isDestructive, true);
  assert.equal(result.severity, 'CATASTROPHIC');
  assert.equal(result.bulkCount, 4382);
});

test('classify: rm -rf / -> catastrophic', () => {
  const result = classifyDestructiveAction('bash', {
    command: 'rm -rf /',
  }, {
    moduleName: 'Shell',
    methodName: 'bash',
    bulkThreshold: 20,
  });

  assert.equal(result.isDestructive, true);
  assert.equal(result.severity, 'CATASTROPHIC');
});

test('classify: updatePaymentMethod -> catastrophic', () => {
  const result = classifyDestructiveAction('Gateway.updatePaymentMethod', {
    cardLast4: '4242',
  }, {
    moduleName: 'Gateway',
    methodName: 'updatePaymentMethod',
    bulkThreshold: 20,
  });

  assert.equal(result.isDestructive, true);
  assert.equal(result.severity, 'CATASTROPHIC');
});

test('classify: count <= threshold without destructive verb -> not destructive', () => {
  const result = classifyDestructiveAction('Gmail.listMessages', {
    count: 10,
    query: 'in:inbox',
  }, {
    moduleName: 'Gmail',
    methodName: 'listMessages',
    bulkThreshold: 20,
  });

  assert.equal(result.isDestructive, false);
});
