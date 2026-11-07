export type TtsEngine = 'app' | 'web';

export interface SpeakOptions {
  /** BCP 47 語言代碼，預設 'zh-TW' */
  lang?: string;
  /** 語速，預設 0.85（比一般慢，給長輩聽） */
  rate?: number;
}

export interface SpeakResult {
  ok: boolean;
  /** 實際使用的引擎（ok 為 true 時才有） */
  engine?: TtsEngine;
  /** 失敗原因，多個引擎的原因以逗號串接，例如 'no_app_handler,no_chinese_voice' */
  reason?: string;
}

export interface VoiceInfo {
  name: string;
  lang: string;
  localService: boolean;
}

export interface TtsDiagnosis {
  inApp: boolean;
  appHandler: boolean | null;
  webSpeech: boolean;
  voices: VoiceInfo[];
  chosenVoice: VoiceInfo | null;
  userAgent: string;
}

export function speak(text: string, options?: SpeakOptions): Promise<SpeakResult>;
export function stop(): void;
export function diagnose(lang?: string): Promise<TtsDiagnosis>;
export function splitText(text: string): string[];
export function pickVoice(voices: SpeechSynthesisVoice[], lang?: string): SpeechSynthesisVoice | null;
