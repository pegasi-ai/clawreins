/**
 * ClawReins Config Manager
 * Manages ClawReins configuration in OpenClaw's openclaw.json
 */

import fs from 'fs-extra';
import path from 'path';
import os from 'os';
import { logger } from '../core/Logger';

const OPENCLAW_HOME = process.env.OPENCLAW_HOME || path.join(os.homedir(), '.openclaw');
const OPENCLAW_CONFIG_FILE = path.join(OPENCLAW_HOME, 'openclaw.json');

export interface OpenClawConfig {
  plugins?: {
    entries?: Record<
      string,
      {
        enabled: boolean;
        config?: Record<string, unknown>;
      }
    >;
    [key: string]: unknown;
  };
  [key: string]: unknown;
}

/**
 * Check if OpenClaw is installed
 */
export async function isOpenClawInstalled(): Promise<boolean> {
  return await fs.pathExists(OPENCLAW_HOME);
}

/**
 * Load OpenClaw's main configuration
 */
export async function loadOpenClawConfig(): Promise<OpenClawConfig | null> {
  try {
    if (!(await fs.pathExists(OPENCLAW_CONFIG_FILE))) {
      return null;
    }
    return await fs.readJson(OPENCLAW_CONFIG_FILE);
  } catch (error) {
    logger.error('Failed to load OpenClaw config', { error });
    return null;
  }
}

/**
 * Save OpenClaw's main configuration
 */
export async function saveOpenClawConfig(config: OpenClawConfig): Promise<void> {
  try {
    await fs.ensureDir(OPENCLAW_HOME);
    await fs.writeJson(OPENCLAW_CONFIG_FILE, config, { spaces: 2 });
    logger.info('OpenClaw config saved', { path: OPENCLAW_CONFIG_FILE });
  } catch (error) {
    logger.error('Failed to save OpenClaw config', { error });
    throw error;
  }
}

/**
 * Register ClawReins plugin in OpenClaw's config (plugins.entries.clawreins)
 */
export async function registerPlugin(
  defaultAction: 'ALLOW' | 'DENY' | 'ASK' = 'ASK'
): Promise<void> {
  const config = await loadOpenClawConfig();

  if (!config) {
    logger.warn('OpenClaw config not found, skipping plugin registration');
    return;
  }

  if (!config.plugins || typeof config.plugins !== 'object') {
    config.plugins = {};
  }

  if (!config.plugins.entries || typeof config.plugins.entries !== 'object') {
    config.plugins.entries = {};
  }

  config.plugins.entries.clawreins = {
    enabled: true,
    config: { defaultAction },
  };

  await saveOpenClawConfig(config);
  logger.info('Registered ClawReins in OpenClaw config (plugins.entries.clawreins)');
}

/**
 * Unregister ClawReins plugin from OpenClaw's config
 */
export async function unregisterPlugin(): Promise<void> {
  const config = await loadOpenClawConfig();

  if (!config?.plugins?.entries) {
    return;
  }

  delete config.plugins.entries.clawreins;
  await saveOpenClawConfig(config);
  logger.info('Unregistered ClawReins plugin from OpenClaw config');
}

/**
 * Check if ClawReins is registered in OpenClaw
 */
export async function isPluginRegistered(): Promise<boolean> {
  const config = await loadOpenClawConfig();
  return !!config?.plugins?.entries?.clawreins;
}
