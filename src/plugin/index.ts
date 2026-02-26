/**
 * ClawReins Plugin Entry Point
 * OpenClaw plugin integration.
 *
 * IMPORTANT: register() must be SYNCHRONOUS — the OpenClaw gateway
 * ignores async plugin registration (the returned promise is not awaited).
 *
 * Hooks:
 *  before_tool_call → api.on() (tool interception)
 */

import { Interceptor } from '../core/Interceptor';
import { PolicyStore } from '../storage/PolicyStore';
import { logger } from '../core/Logger';
import { createToolCallHook, CLAWREINS_RESPOND_TOOL } from './tool-interceptor';
import path from 'path';
import { readFileSync } from 'fs';

export interface ClawReinsConfig {
  enabled?: boolean;
  defaultAction?: 'ALLOW' | 'DENY' | 'ASK';
}

export interface ClawReinsPluginManifest {
  id: string;
  displayName: string;
  version: string;
  configure: {
    command: string;
  };
}

function getPackageVersion(): string {
  try {
    const packageJsonPath = path.join(__dirname, '..', '..', 'package.json');
    const packageJson = JSON.parse(readFileSync(packageJsonPath, 'utf-8')) as { version?: string };
    return packageJson.version || '0.0.0';
  } catch {
    return '0.0.0';
  }
}

export const ClawReinsManifest: ClawReinsPluginManifest = {
  id: 'clawreins',
  displayName: 'Clawreins',
  version: getPackageVersion(),
  configure: {
    command: 'clawreins configure',
  },
};

/**
 * OpenClaw plugin API surface used by ClawReins.
 * Both methods are optional — the gateway may not support all of them.
 */
interface OpenClawPluginApi {
  on?(hookName: string, handler: (...args: unknown[]) => void): void;
  registerTool?(spec: {
    name: string;
    description: string;
    parameters: Record<string, unknown>;
    execute: (...args: unknown[]) => Promise<unknown>;
  }): void;
}

/**
 * Attempt to register the clawreins_respond tool via api.registerTool().
 * Returns true if the call succeeded, false if the API is not available.
 */
function tryRegisterTool(api: OpenClawPluginApi): boolean {
  try {
    if (!api.registerTool) {
      logger.info('[plugin] api.registerTool not available — fallback retry-as-approval');
      return false;
    }
    api.registerTool({
      name: CLAWREINS_RESPOND_TOOL,
      description: 'Respond to a ClawReins security prompt. Call after the user says YES, NO, ALLOW, or provides CONFIRM token.',
      parameters: {
        type: 'object',
        properties: {
          decision: {
            type: 'string',
            enum: ['yes', 'no', 'allow', 'confirm'],
            description: 'The user decision: yes/no/allow, or confirm for strict irreversibility actions.',
          },
          confirmation: {
            type: 'string',
            description: 'Required when decision=confirm. Example: CONFIRM-ABC123',
          },
        },
        required: ['decision'],
      },
      // The actual logic runs in before_tool_call (tool-interceptor.ts).
      // This execute handler exists only because the gateway requires it.
      execute: async () => ({ result: 'Handled by ClawReins hook.' }),
    });
    logger.info(`[plugin] Registered tool: ${CLAWREINS_RESPOND_TOOL}`);
    return true;
  } catch (err) {
    logger.warn(`[plugin] api.registerTool() threw`, { error: err });
    return false;
  }
}

/**
 * Safely attempt to register a hook via api.on().
 * Returns true if the call succeeded (no throw), false otherwise.
 */
function tryOn(
  api: OpenClawPluginApi,
  hookName: string,
  handler: (...args: unknown[]) => void,
  label: string
): boolean {
  try {
    if (!api.on) {
      logger.debug(`[plugin] ${label}: api.on not available`);
      return false;
    }
    api.on(hookName, handler);
    logger.info(`[plugin] ${label}: api.on('${hookName}') succeeded`);
    return true;
  } catch (err) {
    logger.warn(`[plugin] ${label}: api.on('${hookName}') threw`, { error: err });
    return false;
  }
}

export default {
  id: 'clawreins',
  name: 'ClawReins',
  manifest: ClawReinsManifest,

  register(api: OpenClawPluginApi): void {
    logger.info('ClawReins plugin loading...');

    try {
      const policy = PolicyStore.loadSync();
      logger.info('Security policy loaded', {
        defaultAction: policy.defaultAction,
        moduleCount: Object.keys(policy.modules).length,
      });

      const interceptor = new Interceptor(policy);

      // -----------------------------------------------------------------------
      // Hook: before_tool_call — tool interception
      // -----------------------------------------------------------------------
      const toolHook = createToolCallHook(interceptor);
      tryOn(api, 'before_tool_call', toolHook as (...args: unknown[]) => void, 'before_tool_call');

      // -----------------------------------------------------------------------
      // Tool registration: clawreins_respond
      // If available, the LLM sees this tool and calls it with { decision: "yes"|"no"|"allow"|"confirm" }.
      // The actual logic is intercepted in before_tool_call (tool-interceptor.ts).
      // -----------------------------------------------------------------------
      const toolRegistered = tryRegisterTool(api);
      interceptor.respondToolAvailable = toolRegistered;

      logger.info('ClawReins: hook registration complete', {
        respondToolAvailable: toolRegistered,
      });
    } catch (error) {
      logger.error('Failed to initialize ClawReins plugin', { error });
      throw error;
    }
  },
};
