/**
 * ClawReins Init Wizard
 * Interactive setup for ClawReins with OpenClaw
 */

import inquirer from 'inquirer';
import chalk from 'chalk';
import fs from 'fs-extra';
import path from 'path';
import { isOpenClawInstalled, registerPlugin, isPluginRegistered } from '../plugin/config-manager';
import { PolicyStore, PersistedPolicy } from '../storage/PolicyStore';
import { logger, CLAWREINS_DATA_DIR } from '../core/Logger';
import { DEFAULT_POLICY } from '../config';
import { SecurityRule } from '../types';
import { getProtectedModules } from '../plugin/tool-interceptor';
import { syncToolShieldDefaults } from '../toolshield/sync';

const SECURITY_PRESETS = {
  permissive: {
    name: '🟢 Permissive',
    description: 'read: ALLOW, write: ASK, delete: ASK, bash: ASK',
    policy: {
      FileSystem: {
        read: { action: 'ALLOW' as const, description: 'Safe read-only' },
        write: { action: 'ASK' as const, description: 'Needs approval' },
        delete: { action: 'ASK' as const, description: 'Requires confirmation' },
      },
      Shell: {
        bash: { action: 'ASK' as const, description: 'RCE risk' },
        exec: { action: 'ASK' as const, description: 'RCE risk' },
      },
    },
  },
  balanced: {
    name: '🟡 Balanced (Recommended)',
    description: 'read: ALLOW, write: ASK, delete: DENY, bash: ASK',
    policy: DEFAULT_POLICY.modules,
  },
  strict: {
    name: '🔴 Strict',
    description: 'read: ASK, write: ASK, delete: DENY, bash: DENY',
    policy: {
      FileSystem: {
        read: { action: 'ASK' as const, description: 'Confirm all reads' },
        write: { action: 'ASK' as const, description: 'Needs approval' },
        delete: { action: 'DENY' as const, description: 'Strictly prohibited' },
      },
      Shell: {
        bash: { action: 'DENY' as const, description: 'RCE blocked' },
        exec: { action: 'DENY' as const, description: 'RCE blocked' },
      },
    },
  },
};

export async function initWizard(): Promise<void> {
  console.log('');
  console.log(chalk.bold.cyan('═'.repeat(80)));
  console.log(chalk.bold.cyan('   🦞 + 🪢 ClawReins Setup Wizard'));
  console.log(chalk.bold.cyan('   ClawReins is the intervention layer for OpenClaw.'));
  console.log(chalk.bold.cyan('═'.repeat(80)));
  console.log('');

  try {
    // Step 1: Detect OpenClaw
    console.log(chalk.bold('Step 1: Detecting OpenClaw...'));
    const isInstalled = await isOpenClawInstalled();

    if (!isInstalled) {
      console.log('');
      console.log(chalk.red('❌ OpenClaw is not installed or not found.'));
      console.log('');
      console.log(chalk.yellow('Please install OpenClaw first:'));
      console.log(chalk.dim('  npm install -g openclaw'));
      console.log('');
      process.exit(1);
    }

    console.log(chalk.green('✅ OpenClaw detected'));
    console.log('');

    // Check if already registered
    const alreadyRegistered = await isPluginRegistered();
    if (alreadyRegistered) {
      const { shouldReconfigure } = await inquirer.prompt([
        {
          type: 'confirm',
          name: 'shouldReconfigure',
          message: 'ClawReins is already configured. Reconfigure?',
          default: false,
        },
      ]);

      if (!shouldReconfigure) {
        console.log(chalk.yellow('Setup cancelled.'));
        return;
      }
    }

    // Step 2: Choose security level
    console.log(chalk.bold('Step 2: Choose your security level'));
    console.log('');

    const { securityLevel } = await inquirer.prompt([
      {
        type: 'list',
        name: 'securityLevel',
        message: 'Which security policy would you like to use?',
        choices: [
          {
            name: `${SECURITY_PRESETS.permissive.name} - ${SECURITY_PRESETS.permissive.description}`,
            value: 'permissive',
          },
          {
            name: `${SECURITY_PRESETS.balanced.name} - ${SECURITY_PRESETS.balanced.description}`,
            value: 'balanced',
          },
          {
            name: `${SECURITY_PRESETS.strict.name} - ${SECURITY_PRESETS.strict.description}`,
            value: 'strict',
          },
          {
            name: '⚙️  Custom (configure manually after setup)',
            value: 'custom',
          },
        ],
        default: 'balanced',
      },
    ]);

    console.log('');

    // Step 3: Select modules to protect
    console.log(chalk.bold('Step 3: Select which OpenClaw tools to protect'));
    console.log('');

    const availableModules = getProtectedModules();

    const { selectedModules } = await inquirer.prompt([
      {
        type: 'checkbox',
        name: 'selectedModules',
        message: 'Which tool modules should ClawReins intercept?',
        choices: availableModules.map((mod) => ({
          name: mod,
          value: mod,
          checked: ['FileSystem', 'Shell', 'Browser'].includes(mod), // Default selections
        })),
      },
    ]);

    console.log('');

    // Step 4: Create the policy
    console.log(chalk.bold('Step 4: Creating security policy...'));

    const selectedPreset = SECURITY_PRESETS[securityLevel as keyof typeof SECURITY_PRESETS];
    const modules: Record<string, Record<string, SecurityRule>> = {};

    if (securityLevel !== 'custom' && selectedPreset) {
      // Apply preset to selected modules only
      selectedModules.forEach((moduleName: string) => {
        if (selectedPreset.policy[moduleName as keyof typeof selectedPreset.policy]) {
          modules[moduleName] =
            selectedPreset.policy[moduleName as keyof typeof selectedPreset.policy];
        } else {
          // Default to ASK for modules not in preset
          modules[moduleName] = {
            '*': { action: 'ASK', description: 'Default security' },
          };
        }
      });
    }

    const policy: PersistedPolicy = {
      version: '1.0.0',
      defaultAction: 'ASK',
      modules,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };

    await PolicyStore.save(policy);
    console.log(chalk.green(`✅ Policy saved to ${PolicyStore.getPath()}`));
    console.log('');

    // Step 5: Install plugin in OpenClaw
    console.log(chalk.bold('Step 5: Registering with OpenClaw...'));

    // Find the project root (where openclaw.plugin.json lives)
    const pluginRoot = path.resolve(__dirname, '..', '..');
    const manifestPath = path.join(pluginRoot, 'openclaw.plugin.json');
    const manifestExists = await fs.pathExists(manifestPath);

    if (manifestExists) {
      console.log(chalk.dim(`  Plugin manifest found: ${manifestPath}`));
      console.log(chalk.dim(`  Install with: openclaw plugins install --link ${pluginRoot}`));
    }

    await registerPlugin(policy.defaultAction);
    console.log(chalk.green('✅ ClawReins registered in OpenClaw config'));
    console.log('');

    // Step 6: Enable ToolShield defaults (automatic)
    console.log(chalk.bold('Step 6: Enabling ToolShield defaults...'));
    const toolShieldResult = await syncToolShieldDefaults();
    if (toolShieldResult.synced) {
      console.log(chalk.green(`✅ ${toolShieldResult.message}`));
      if (toolShieldResult.installedNow) {
        console.log(chalk.dim('  ToolShield was installed automatically via pip.'));
      }
    } else {
      console.log(chalk.yellow(`⚠️  ${toolShieldResult.message}`));
      console.log(
        chalk.dim('  You can retry manually with: clawreins toolshield-sync')
      );
    }
    console.log('');

    // Success summary
    console.log(chalk.bold.green('═'.repeat(80)));
    console.log(chalk.bold.green('   ✅ ClawReins installed successfully!'));
    console.log(chalk.bold.green('═'.repeat(80)));
    console.log('');

    console.log(chalk.bold('Configuration:'));
    console.log(chalk.dim(`  Policy:     ${PolicyStore.getPath()}`));
    console.log(chalk.dim(`  Audit log:  ${CLAWREINS_DATA_DIR}/decisions.jsonl`));
    console.log(chalk.dim(`  Stats:      ${CLAWREINS_DATA_DIR}/stats.json`));
    console.log('');

    console.log(chalk.bold('Next steps:'));
    if (manifestExists) {
      console.log(
        chalk.cyan('  1. Install plugin:') +
          chalk.dim(`    openclaw plugins install --link ${pluginRoot}`)
      );
    }
    console.log(chalk.cyan('  2. Edit policy:') + chalk.dim('       clawreins policy'));
    console.log(chalk.cyan('  3. Sync ToolShield:') + chalk.dim('   clawreins toolshield-sync'));
    console.log(chalk.cyan('  4. View audit trail:') + chalk.dim('  clawreins audit'));
    console.log('');
  } catch (error) {
    console.error(chalk.red('❌ Setup failed:'), error);
    logger.error('Init wizard failed', { error });
    process.exit(1);
  }
}
