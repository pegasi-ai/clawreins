/**
 * ClawReins StatsTracker
 * Tracks statistics about decisions (~/.openclaw/clawreins/stats.json)
 */

import fs from 'fs-extra';
import path from 'path';
import { CLAWREINS_DATA_DIR, logger } from '../core/Logger';

const STATS_FILE = path.join(CLAWREINS_DATA_DIR, 'stats.json');

export interface Stats {
  totalCalls: number;
  approved: number;
  rejected: number;
  blocked: number;
  allowed: number;
  avgDecisionTime: number;
  lastReset: string;
}

/** Serializes concurrent writes to prevent lost increments. */
let writeChain = Promise.resolve();

export class StatsTracker {
  /**
   * Load stats from disk
   */
  static async load(): Promise<Stats> {
    try {
      await fs.ensureDir(CLAWREINS_DATA_DIR);

      if (await fs.pathExists(STATS_FILE)) {
        return await fs.readJson(STATS_FILE);
      } else {
        // Initialize with zeros
        const initialStats: Stats = {
          totalCalls: 0,
          approved: 0,
          rejected: 0,
          blocked: 0,
          allowed: 0,
          avgDecisionTime: 0,
          lastReset: new Date().toISOString(),
        };
        await this.save(initialStats);
        return initialStats;
      }
    } catch (error) {
      logger.error('Failed to load stats', { error });
      throw error;
    }
  }

  /**
   * Save stats to disk
   */
  static async save(stats: Stats): Promise<void> {
    try {
      await fs.ensureDir(CLAWREINS_DATA_DIR);
      await fs.writeJson(STATS_FILE, stats, { spaces: 2 });
    } catch (error) {
      logger.error('Failed to save stats', { error });
      throw error;
    }
  }

  /**
   * Increment a stat counter and update average decision time
   */
  static async increment(
    decision: 'ALLOWED' | 'APPROVED' | 'REJECTED' | 'BLOCKED',
    decisionTime: number
  ): Promise<void> {
    // Serialize writes to prevent concurrent load/modify/save from losing increments
    const op = writeChain.then(async () => {
      const stats = await this.load();

      stats.totalCalls++;

      switch (decision) {
        case 'ALLOWED':
          stats.allowed++;
          break;
        case 'APPROVED':
          stats.approved++;
          break;
        case 'REJECTED':
          stats.rejected++;
          break;
        case 'BLOCKED':
          stats.blocked++;
          break;
      }

      // Update rolling average decision time
      const totalDecisionTime = stats.avgDecisionTime * (stats.totalCalls - 1) + decisionTime;
      stats.avgDecisionTime = Math.round(totalDecisionTime / stats.totalCalls);

      await this.save(stats);
    });
    writeChain = op.catch(() => {});
    return op;
  }

  /**
   * Reset all stats to zero
   */
  static async reset(): Promise<void> {
    const resetStats: Stats = {
      totalCalls: 0,
      approved: 0,
      rejected: 0,
      blocked: 0,
      allowed: 0,
      avgDecisionTime: 0,
      lastReset: new Date().toISOString(),
    };
    await this.save(resetStats);
    logger.info('Stats reset');
  }

  /**
   * Get the stats file path
   */
  static getPath(): string {
    return STATS_FILE;
  }
}
