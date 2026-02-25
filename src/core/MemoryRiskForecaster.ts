/**
 * Memory Risk Forecaster
 *
 * Detects multi-turn risk drift from accumulated execution memory.
 * Signals:
 *  - drift score: intent drift from early-session baseline
 *  - salami index: benign-looking steps composing into harmful chains
 *  - commitment creep: cumulative irreversibility trend
 */

import { IrreversibilityAssessment } from './IrreversibilityScorer';

type AttackStage =
  | 'recon'
  | 'collection'
  | 'package'
  | 'exfil'
  | 'destruct'
  | 'escalate'
  | 'conceal';

interface MemoryEvent {
  timestamp: string;
  moduleName: string;
  methodName: string;
  text: string;
  irreversibility: number;
  stages: AttackStage[];
}

interface SessionMemoryState {
  baselineIntent: string;
  baselineModule: string;
  events: MemoryEvent[];
  createdAt: string;
  updatedAt: string;
}

export interface SimulatedPath {
  name: string;
  risk: number;
  rationale: string;
}

export interface MemoryRiskAssessment {
  driftScore: number;
  salamiIndex: number;
  commitmentCreep: number;
  overallRisk: number;
  shouldPause: boolean;
  simulatedPaths: SimulatedPath[];
  summary: string;
}

const MAX_EVENTS = 40;
const ATTACK_PAUSE_THRESHOLD = 72;

const STOPWORDS = new Set([
  'the',
  'a',
  'an',
  'to',
  'and',
  'or',
  'of',
  'for',
  'in',
  'on',
  'with',
  'from',
  'this',
  'that',
  'is',
  'are',
  'be',
  'by',
  'as',
  'at',
  'it',
  'if',
  'into',
  'about',
  'then',
  'than',
  'just',
  'can',
  'could',
  'should',
  'would',
]);

function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}

function tokenize(text: string): Set<string> {
  const tokens = (text.toLowerCase().match(/[a-z0-9_]+/g) || [])
    .filter((t) => t.length > 2 && !STOPWORDS.has(t));
  return new Set(tokens);
}

function jaccardDistance(left: Set<string>, right: Set<string>): number {
  if (left.size === 0 || right.size === 0) {
    return 0;
  }
  let intersection = 0;
  for (const token of left) {
    if (right.has(token)) {
      intersection += 1;
    }
  }
  const union = left.size + right.size - intersection;
  if (union === 0) {
    return 0;
  }
  return 1 - intersection / union;
}

function stringifyParams(params: Record<string, unknown>): string {
  try {
    const raw = JSON.stringify(params);
    return raw.length > 800 ? `${raw.slice(0, 797)}...` : raw;
  } catch {
    return String(params);
  }
}

function containsAny(text: string, patterns: RegExp[]): boolean {
  return patterns.some((pattern) => pattern.test(text));
}

export class MemoryRiskForecaster {
  private sessions = new Map<string, SessionMemoryState>();

  assess(
    sessionKey: string,
    moduleName: string,
    methodName: string,
    params: Record<string, unknown>,
    irreversibility: IrreversibilityAssessment
  ): MemoryRiskAssessment {
    const state = this.getOrCreateSession(sessionKey, moduleName, params);
    const text = stringifyParams(params);
    const stages = this.detectStages(moduleName, methodName, text);
    const now = new Date().toISOString();

    state.events.push({
      timestamp: now,
      moduleName,
      methodName,
      text,
      irreversibility: irreversibility.score,
      stages,
    });
    state.updatedAt = now;
    if (state.events.length > MAX_EVENTS) {
      state.events.shift();
    }

    const driftScore = this.computeDriftScore(state);
    const salamiIndex = this.computeSalamiIndex(state);
    const commitmentCreep = this.computeCommitmentCreep(state);
    const simulatedPaths = this.simulateNextTurnPaths(state);

    const topSimulatedRisk = simulatedPaths.length > 0 ? simulatedPaths[0].risk : 0;
    const blendedSignals = driftScore * 0.3 + salamiIndex * 0.35 + commitmentCreep * 0.35;
    const overallRisk = Math.round(clamp(blendedSignals * 0.7 + topSimulatedRisk * 0.3, 0, 100));
    const shouldPause = overallRisk >= ATTACK_PAUSE_THRESHOLD || topSimulatedRisk >= 88;
    const topPath = simulatedPaths[0];
    const summary = topPath
      ? `Memory trajectory risk ${overallRisk}/100. Likely next risk: ${topPath.name} (${topPath.risk}/100).`
      : `Memory trajectory risk ${overallRisk}/100 with no single dominant path.`;

    return {
      driftScore,
      salamiIndex,
      commitmentCreep,
      overallRisk,
      shouldPause,
      simulatedPaths,
      summary,
    };
  }

  private getOrCreateSession(
    sessionKey: string,
    moduleName: string,
    params: Record<string, unknown>
  ): SessionMemoryState {
    const existing = this.sessions.get(sessionKey);
    if (existing) {
      return existing;
    }

    const now = new Date().toISOString();
    const baselineIntent = stringifyParams(params);
    const created: SessionMemoryState = {
      baselineIntent,
      baselineModule: moduleName,
      events: [],
      createdAt: now,
      updatedAt: now,
    };
    this.sessions.set(sessionKey, created);
    return created;
  }

  private computeDriftScore(state: SessionMemoryState): number {
    const baselineTokens = tokenize(state.baselineIntent);
    const recentText = state.events
      .slice(-8)
      .map((event) => event.text)
      .join(' ');
    const recentTokens = tokenize(recentText);
    let drift = Math.round(jaccardDistance(baselineTokens, recentTokens) * 100);

    const hasModuleDrift = state.events.length >= 4
      && state.events.slice(-4).some((event) => event.moduleName !== state.baselineModule);
    if (hasModuleDrift) {
      drift += 10;
    }

    return clamp(drift, 0, 100);
  }

  private computeSalamiIndex(state: SessionMemoryState): number {
    const window = state.events.slice(-12);
    if (window.length === 0) {
      return 0;
    }

    const stages = new Set<AttackStage>();
    for (const event of window) {
      for (const stage of event.stages) {
        stages.add(stage);
      }
    }

    let score = 0;

    if (this.hasTransition(window, 'recon', 'collection')) score += 15;
    if (this.hasTransition(window, 'collection', 'package')) score += 20;
    if (this.hasTransition(window, 'package', 'exfil')) score += 30;
    if (this.hasTransition(window, 'collection', 'destruct')) score += 30;
    if (this.hasTransition(window, 'recon', 'destruct')) score += 25;

    if (stages.size >= 3 && (stages.has('exfil') || stages.has('destruct'))) {
      score += 20;
    }

    const mostlyLowRiskSteps = window.filter((event) => event.irreversibility < 55).length >= Math.ceil(window.length * 0.7);
    if (mostlyLowRiskSteps && (stages.has('exfil') || stages.has('destruct'))) {
      score += 15;
    }

    return clamp(score, 0, 100);
  }

  private hasTransition(window: MemoryEvent[], first: AttackStage, second: AttackStage): boolean {
    let firstSeen = false;
    for (const event of window) {
      if (event.stages.includes(first)) {
        firstSeen = true;
      }
      if (firstSeen && event.stages.includes(second)) {
        return true;
      }
    }
    return false;
  }

  private computeCommitmentCreep(state: SessionMemoryState): number {
    const window = state.events.slice(-10);
    if (window.length === 0) {
      return 0;
    }

    const irreversibilityValues = window.map((event) => event.irreversibility);
    const avg = irreversibilityValues.reduce((acc, value) => acc + value, 0) / irreversibilityValues.length;
    const slope = irreversibilityValues.length >= 2
      ? irreversibilityValues[irreversibilityValues.length - 1] - irreversibilityValues[0]
      : 0;
    const highCommitmentActions = irreversibilityValues.filter((value) => value >= 75).length;

    let score = avg * 0.5 + Math.max(0, slope) * 1.0 + highCommitmentActions * 10;
    if (window.some((event) => event.stages.includes('destruct'))) {
      score += 10;
    }
    if (window.some((event) => event.stages.includes('exfil'))) {
      score += 8;
    }

    return Math.round(clamp(score, 0, 100));
  }

  private simulateNextTurnPaths(state: SessionMemoryState): SimulatedPath[] {
    const window = state.events.slice(-12);
    const text = window.map((event) => event.text).join(' ');
    const stageSet = new Set<AttackStage>();
    for (const event of window) {
      for (const stage of event.stages) {
        stageSet.add(stage);
      }
    }

    const candidates: SimulatedPath[] = [];

    if (
      containsAny(text, [/wire transfer|bank transfer|payment|invoice|routing number|swift|ach/i])
    ) {
      candidates.push({
        name: 'Business email compromise / payment fraud',
        risk: 92,
        rationale: 'Financial transfer language detected in multi-turn memory.',
      });
    }

    if (containsAny(text, [/password|2fa|token|credential|reset code|api key|secret/i])) {
      candidates.push({
        name: 'Credential theft and account takeover',
        risk: stageSet.has('exfil') ? 90 : 84,
        rationale: 'Credential-related context appears with execution trajectory.',
      });
    }

    if (stageSet.has('recon') && stageSet.has('collection')) {
      candidates.push({
        name: 'Data exfiltration escalation',
        risk: stageSet.has('package') || stageSet.has('exfil') ? 88 : 78,
        rationale: 'Recon + collection chain indicates likely package/send next step.',
      });
    }

    if (stageSet.has('destruct') || containsAny(text, [/rm -rf|delete|drop table|truncate|wipe|format/i])) {
      candidates.push({
        name: 'Irreversible data destruction',
        risk: 89,
        rationale: 'Destructive intent indicators present in memory sequence.',
      });
    }

    if (
      containsAny(text, [/security alert|suspicious activity|fraud alert|breach/i])
      && containsAny(text, [/delete|trash|archive|mark.*read|hide|suppress/i])
    ) {
      candidates.push({
        name: 'Security-signal concealment',
        risk: 86,
        rationale: 'Memory contains threat-notice and concealment actions in the same chain.',
      });
    }

    if (containsAny(text, [/sudo|chmod|chown|grant|admin|privilege|root/i])) {
      candidates.push({
        name: 'Privilege escalation and persistence',
        risk: 84,
        rationale: 'Privilege-escalation markers detected in recent turns.',
      });
    }

    if (candidates.length === 0 && this.computeCommitmentCreep(state) >= 70) {
      candidates.push({
        name: 'High-commitment unsafe trajectory',
        risk: 76,
        rationale: 'No single signature matched, but irreversibility trend is steep.',
      });
    }

    candidates.sort((a, b) => b.risk - a.risk);
    return candidates.slice(0, 3);
  }

  private detectStages(moduleName: string, methodName: string, text: string): AttackStage[] {
    const stages = new Set<AttackStage>();
    const lowerModule = moduleName.toLowerCase();
    const lowerMethod = methodName.toLowerCase();

    if (
      (lowerModule === 'filesystem' && (lowerMethod === 'read' || lowerMethod === 'list'))
      || (lowerModule === 'browser' && (lowerMethod === 'navigate' || lowerMethod === 'screenshot'))
      || (lowerModule === 'gateway' && (lowerMethod === 'listsessions' || lowerMethod === 'listnodes'))
      || (lowerModule === 'network' && lowerMethod === 'fetch')
    ) {
      stages.add('recon');
    }

    if (
      lowerModule === 'filesystem'
      && (lowerMethod === 'read' || lowerMethod === 'write' || lowerMethod === 'edit')
      && containsAny(text, [/confidential|customer|finance|invoice|credential|token|secret|key/i])
    ) {
      stages.add('collection');
    }

    if (
      lowerModule === 'filesystem'
      && (lowerMethod === 'write' || lowerMethod === 'edit')
      && containsAny(text, [/zip|archive|bundle|report|export|compile/i])
    ) {
      stages.add('package');
    }

    if (
      (lowerModule === 'network' && (lowerMethod === 'request' || lowerMethod === 'webhook' || lowerMethod === 'download'))
      || (lowerModule === 'gateway' && lowerMethod === 'sendmessage')
    ) {
      stages.add('exfil');
    }

    if (
      (lowerModule === 'filesystem' && lowerMethod === 'delete')
      || (lowerModule === 'shell' && (lowerMethod === 'bash' || lowerMethod === 'exec')
        && containsAny(text, [/rm -rf|del \/s|drop table|truncate|wipe|format|shred/i]))
    ) {
      stages.add('destruct');
    }

    if (
      lowerModule === 'shell'
      && (lowerMethod === 'bash' || lowerMethod === 'exec')
      && containsAny(text, [/sudo|chmod|chown|grant|root|administrator|privilege/i])
    ) {
      stages.add('escalate');
    }

    if (containsAny(text, [/archive|mark.*read|delete alerts|hide alert|suppress/i])) {
      stages.add('conceal');
    }

    return Array.from(stages);
  }
}
