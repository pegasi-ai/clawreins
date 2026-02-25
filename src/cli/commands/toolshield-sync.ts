import chalk from 'chalk';
import { syncToolShieldDefaults } from '../../toolshield/sync';
import { logger } from '../../core/Logger';

interface ToolShieldSyncCommandOptions {
  model?: string;
  agentsFile?: string;
  bundledDir?: string;
  noInstall?: boolean;
  append?: boolean;
}

export async function toolShieldSyncCommand(options: ToolShieldSyncCommandOptions): Promise<void> {
  try {
    const result = await syncToolShieldDefaults({
      model: options.model,
      agentsFile: options.agentsFile,
      bundledDir: options.bundledDir,
      installIfMissing: !options.noInstall,
      unloadFirst: !options.append,
    });

    if (result.synced) {
      console.log(chalk.green(`✅ ${result.message}`));
      console.log(chalk.yellow('⚠️  Restart OpenClaw for changes to take effect: openclaw restart'));
      return;
    }

    console.log(chalk.yellow(`⚠️  ${result.message}`));
    console.log(chalk.dim('Run again after resolving ToolShield/Python availability.'));
  } catch (error) {
    console.error(chalk.red('❌ ToolShield sync failed:'), error);
    logger.error('ToolShield sync command failed', { error });
    process.exit(1);
  }
}
