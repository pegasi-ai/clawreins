/**
 * Browser challenge detection (CAPTCHA / Cloudflare wall / 2FA prompts).
 *
 * This detector intentionally favors recall over precision, then marks uncertain
 * cases so the agent can fall back to screenshot + vision review.
 */

export type BrowserChallengeLevel = 'none' | 'possible' | 'likely';
export type BrowserChallengeKind = 'captcha' | '2fa' | 'mixed' | 'unknown';

export interface BrowserChallengeSignal {
  level: BrowserChallengeLevel;
  kind: BrowserChallengeKind;
  reasons: string[];
}

const CAPTCHA_STRONG_PATTERNS: Array<[RegExp, string]> = [
  [/\bg-recaptcha\b/i, 'Detected g-recaptcha marker'],
  [/\bhcaptcha\b/i, 'Detected hCaptcha marker'],
  [/\bcf-turnstile\b|\bturnstile\b/i, 'Detected Cloudflare Turnstile marker'],
  [/\barkose\b|\bfuncaptcha\b/i, 'Detected Arkose/FunCaptcha marker'],
  [/\brecaptcha\b/i, 'Detected reCAPTCHA marker'],
  [/\bcaptcha\b/i, 'Detected CAPTCHA keyword'],
];

const TWO_FACTOR_STRONG_PATTERNS: Array<[RegExp, string]> = [
  [/\b2fa\b|two[ -]?factor/i, 'Detected 2FA keyword'],
  [/one[ -]?time password|\botp\b/i, 'Detected OTP prompt'],
  [/verification code|security code|authenticator/i, 'Detected verification-code prompt'],
  [/\btotp\b|passkey/i, 'Detected strong auth challenge marker'],
  [/sms code|email code|login code/i, 'Detected out-of-band code prompt'],
];

const HUMAN_CHECK_UNCERTAIN_PATTERNS: Array<[RegExp, string]> = [
  [/verify (that )?you are human/i, 'Detected human-verification copy'],
  [/are you human|i am not a robot/i, 'Detected anti-bot challenge copy'],
  [/additional verification required|unusual traffic/i, 'Detected generic verification wall'],
  [/challenge required|security challenge/i, 'Detected generic challenge wording'],
  [/confirm it\'s you|confirm your identity/i, 'Detected account-verification wording'],
  [/cloudflare/i, 'Detected Cloudflare marker'],
];

function safeStringify(input: unknown): string {
  try {
    return JSON.stringify(input);
  } catch {
    return String(input);
  }
}

function scoreMatches(text: string, patterns: Array<[RegExp, string]>, weight: number): [number, string[]] {
  let score = 0;
  const reasons: string[] = [];
  for (const [pattern, reason] of patterns) {
    if (pattern.test(text)) {
      score += weight;
      reasons.push(reason);
    }
  }
  return [score, reasons];
}

export function detectBrowserChallenge(
  toolName: string,
  params: Record<string, unknown>
): BrowserChallengeSignal {
  const loweredTool = toolName.toLowerCase();
  const browserRelevant = ['navigate', 'click', 'type', 'evaluate', 'screenshot'].includes(loweredTool);
  if (!browserRelevant) {
    return { level: 'none', kind: 'unknown', reasons: [] };
  }

  const text = safeStringify(params).toLowerCase();
  const hasIframeHint = /\biframe\b|frame\b/.test(text);

  const [captchaScore, captchaReasons] = scoreMatches(text, CAPTCHA_STRONG_PATTERNS, 25);
  const [twoFactorScore, twoFactorReasons] = scoreMatches(text, TWO_FACTOR_STRONG_PATTERNS, 25);
  const [uncertainScore, uncertainReasons] = scoreMatches(text, HUMAN_CHECK_UNCERTAIN_PATTERNS, 15);

  let totalCaptcha = captchaScore;
  let totalTwoFactor = twoFactorScore;
  const reasons = [...captchaReasons, ...twoFactorReasons, ...uncertainReasons];

  if (hasIframeHint && (captchaScore > 0 || uncertainScore > 0)) {
    totalCaptcha += 20;
    reasons.push('iframe + challenge markers detected (common CAPTCHA embedding pattern)');
  }

  if (hasIframeHint && twoFactorScore > 0) {
    totalTwoFactor += 10;
    reasons.push('iframe + 2FA markers detected');
  }

  const strongest = Math.max(totalCaptcha, totalTwoFactor);
  const combined = totalCaptcha + totalTwoFactor + uncertainScore;

  let kind: BrowserChallengeKind = 'unknown';
  if (totalCaptcha > 0 && totalTwoFactor > 0) {
    kind = 'mixed';
  } else if (totalCaptcha > 0) {
    kind = 'captcha';
  } else if (totalTwoFactor > 0) {
    kind = '2fa';
  }

  if (strongest >= 45 || combined >= 65) {
    return { level: 'likely', kind, reasons };
  }

  if (strongest >= 25 || uncertainScore >= 20 || combined >= 40) {
    return { level: 'possible', kind: kind === 'unknown' ? 'unknown' : kind, reasons };
  }

  return { level: 'none', kind: 'unknown', reasons: [] };
}
