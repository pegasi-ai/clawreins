import test from 'node:test';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import os from 'node:os';
import path from 'node:path';
import { mkdtempSync, mkdirSync } from 'node:fs';

const openclawHome = mkdtempSync(path.join(os.tmpdir(), 'clawreins-destructive-tests-'));
mkdirSync(openclawHome, { recursive: true });
process.env.OPENCLAW_HOME = openclawHome;
process.env.CLAWREINS_DESTRUCTIVE_GATING = 'on';
process.env.CLAWREINS_BULK_THRESHOLD = '20';

const require = createRequire(import.meta.url);
const { Interceptor } = require('../dist/core/Interceptor.js');
const {
  createToolCallHook,
  CLAWREINS_RESPOND_TOOL,
} = require('../dist/plugin/tool-interceptor.js');

function allowAllPolicy() {
  return {
    defaultAction: 'ALLOW',
    modules: {},
  };
}

test('destructive tool call is blocked without approval', async () => {
  const interceptor = new Interceptor(allowAllPolicy());
  interceptor.respondToolAvailable = true;
  const hook = createToolCallHook(interceptor);

  const result = await hook(
    {
      toolName: 'write',
      params: {
        path: '/tmp/demo.txt',
        content: 'overwrite this file',
      },
    },
    {
      toolName: 'write',
      sessionKey: 'it:no-approval',
    }
  );

  assert.equal(result.block, true);
});

test('HIGH destructive action executes after YES approval', async () => {
  const interceptor = new Interceptor(allowAllPolicy());
  interceptor.respondToolAvailable = true;
  const hook = createToolCallHook(interceptor);
  const sessionKey = 'it:high-yes';

  const first = await hook(
    {
      toolName: 'write',
      params: {
        path: '/tmp/high-risk.txt',
        content: 'overwrite with new content',
      },
    },
    {
      toolName: 'write',
      sessionKey,
    }
  );

  assert.equal(first.block, true);

  const yesDecision = await hook(
    {
      toolName: CLAWREINS_RESPOND_TOOL,
      params: { decision: 'yes' },
    },
    {
      toolName: CLAWREINS_RESPOND_TOOL,
      sessionKey,
    }
  );

  assert.equal(yesDecision.block, true);

  const second = await hook(
    {
      toolName: 'write',
      params: {
        path: '/tmp/high-risk.txt',
        content: 'overwrite with new content',
      },
    },
    {
      toolName: 'write',
      sessionKey,
    }
  );

  assert.notEqual(second.block, true);
});

test('CATASTROPHIC action requires CONFIRM token (YES is insufficient)', async () => {
  const interceptor = new Interceptor(allowAllPolicy());
  interceptor.respondToolAvailable = true;
  const hook = createToolCallHook(interceptor);
  const sessionKey = 'it:cat-confirm';

  const first = await hook(
    {
      toolName: 'bash',
      params: { command: 'rm -rf /' },
    },
    {
      toolName: 'bash',
      sessionKey,
    }
  );

  assert.equal(first.block, true);
  assert.match(first.blockReason || '', /CONFIRM-/);

  const yesDecision = await hook(
    {
      toolName: CLAWREINS_RESPOND_TOOL,
      params: { decision: 'yes' },
    },
    {
      toolName: CLAWREINS_RESPOND_TOOL,
      sessionKey,
    }
  );

  assert.equal(yesDecision.block, true);
  assert.match(yesDecision.blockReason || '', /not sufficient/i);

  const token = (first.blockReason || '').match(/CONFIRM-[A-Z0-9]+/)?.[0];
  assert.ok(token, 'expected confirmation token in block reason');

  const confirmDecision = await hook(
    {
      toolName: CLAWREINS_RESPOND_TOOL,
      params: { decision: 'confirm', confirmation: token },
    },
    {
      toolName: CLAWREINS_RESPOND_TOOL,
      sessionKey,
    }
  );

  assert.equal(confirmDecision.block, true);
  assert.match(confirmDecision.blockReason || '', /explicitly confirmed/i);

  const second = await hook(
    {
      toolName: 'bash',
      params: { command: 'rm -rf /' },
    },
    {
      toolName: 'bash',
      sessionKey,
    }
  );

  assert.notEqual(second.block, true);
});
