/**
 * ClawReins Config Manager
 * Manages ClawReins configuration in OpenClaw's openclaw.json
 */

import fs from 'fs-extra';
import path from 'path';
import os from 'os';
import { logger } from '../core/Logger';

export interface OpenClawPaths {
  openclawHome: string;
  openclawConfig: string;
  pluginId: string;
  pluginDir: string;
}

export function getOpenClawPaths(): OpenClawPaths {
  const openclawHome = process.env.OPENCLAW_HOME || path.join(os.homedir(), '.openclaw');
  const openclawConfig = process.env.OPENCLAW_CONFIG || path.join(openclawHome, 'openclaw.json');
  const pluginId = process.env.OPENCLAW_PLUGIN_ID || 'clawreins';
  const pluginDir = process.env.OPENCLAW_PLUGIN_DIR || path.join(openclawHome, 'extensions', pluginId);

  return {
    openclawHome,
    openclawConfig,
    pluginId,
    pluginDir,
  };
}

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
  const { openclawHome } = getOpenClawPaths();
  return await fs.pathExists(openclawHome);
}

/**
 * Load OpenClaw's main configuration
 */
export async function loadOpenClawConfig(): Promise<OpenClawConfig | null> {
  const { openclawConfig } = getOpenClawPaths();
  try {
    if (!(await fs.pathExists(openclawConfig))) {
      return null;
    }
    return await fs.readJson(openclawConfig);
  } catch (error) {
    logger.error('Failed to load OpenClaw config', { error, path: openclawConfig });
    return null;
  }
}

/**
 * Save OpenClaw's main configuration
 */
export async function saveOpenClawConfig(config: OpenClawConfig): Promise<void> {
  const { openclawConfig } = getOpenClawPaths();
  try {
    await fs.ensureDir(path.dirname(openclawConfig));
    await fs.writeJson(openclawConfig, config, { spaces: 2 });
    logger.info('OpenClaw config saved', { path: openclawConfig });
  } catch (error) {
    logger.error('Failed to save OpenClaw config', { error, path: openclawConfig });
    throw error;
  }
}

/**
 * Register ClawReins plugin in OpenClaw's config (plugins.entries.<pluginId>)
 */
export async function registerPlugin(
  defaultAction: 'ALLOW' | 'DENY' | 'ASK' = 'ASK'
): Promise<void> {
  const { pluginId } = getOpenClawPaths();
  const config = (await loadOpenClawConfig()) || {};

  if (!config.plugins || typeof config.plugins !== 'object') {
    config.plugins = {};
  }

  if (!config.plugins.entries || typeof config.plugins.entries !== 'object') {
    config.plugins.entries = {};
  }

  config.plugins.entries[pluginId] = {
    enabled: true,
    config: { defaultAction },
  };

  await saveOpenClawConfig(config);
  logger.info('Registered plugin in OpenClaw config', {
    pluginId,
    path: getOpenClawPaths().openclawConfig,
  });
}

/**
 * Unregister ClawReins plugin from OpenClaw's config
 */
export async function unregisterPlugin(): Promise<void> {
  const { pluginId } = getOpenClawPaths();
  const config = await loadOpenClawConfig();

  if (!config?.plugins?.entries) {
    return;
  }

  delete config.plugins.entries[pluginId];
  await saveOpenClawConfig(config);
  logger.info('Unregistered plugin from OpenClaw config', {
    pluginId,
    path: getOpenClawPaths().openclawConfig,
  });
}

/**
 * Check if ClawReins is registered in OpenClaw
 */
export async function isPluginRegistered(): Promise<boolean> {
  const { pluginId } = getOpenClawPaths();
  const config = await loadOpenClawConfig();
  return !!config?.plugins?.entries?.[pluginId];
}
