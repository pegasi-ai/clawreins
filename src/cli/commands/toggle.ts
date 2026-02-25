/**
 * ClawReins Enable/Disable Commands
 */

import chalk from 'chalk';
import { loadOpenClawConfig, saveOpenClawConfig } from '../../plugin/config-manager';
import { logger } from '../../core/Logger';

export async function disableCommand(): Promise<void> {
  try {
    const config = await loadOpenClawConfig();

    if (!config?.plugins?.entries?.clawreins) {
      console.log(chalk.yellow('ClawReins is not registered in OpenClaw. Run: clawreins init'));
      process.exit(0);
    }

    config.plugins.entries.clawreins.enabled = false;
    await saveOpenClawConfig(config);

    console.log(chalk.green('ClawReins disabled'));
  } catch (error) {
    console.error(chalk.red('Failed to disable ClawReins:'), error);
    logger.error('Disable command failed', { error });
    process.exit(1);
  }
}

export async function enableCommand(): Promise<void> {
  try {
    const config = await loadOpenClawConfig();

    if (!config?.plugins?.entries?.clawreins) {
      console.log(chalk.yellow('ClawReins is not registered in OpenClaw. Run: clawreins init'));
      process.exit(0);
    }

    config.plugins.entries.clawreins.enabled = true;
    await saveOpenClawConfig(config);

    console.log(chalk.green('ClawReins enabled'));
  } catch (error) {
    console.error(chalk.red('Failed to enable ClawReins:'), error);
    logger.error('Enable command failed', { error });
    process.exit(1);
  }
}
