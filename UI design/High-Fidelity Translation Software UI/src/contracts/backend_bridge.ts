import type { CapabilityMap } from "./capability_map";
import type { ConsensusDTO } from "./consensus_dto";
import type { ErrorCode } from "./error_code";
import type { SelfDecisionStatusDTO } from "./learning_strategy";
import type { ProviderHealthDTO } from "./provider_health";
import type { TaskStatus } from "./task_status";
import type { WorkflowMode } from "./workflow_mode";

export interface TranslationRequestDTO {
  text: string;
  source_lang: string;
  target_lang: string;
  topic: string;
  mode: string;
  workflow_mode?: WorkflowMode;
}

export interface TranslationResultDTO {
  ok: boolean;
  run_id: string;
  task_status: TaskStatus;
  error_code: ErrorCode;
  message?: string;
  consensus: ConsensusDTO;
  candidates: string[];
}

interface QtContractBridge {
  getCapabilities(callback: (payload: string) => void): void;
  getSelfDecisionStatus(callback: (payload: string) => void): void;
  getProviderHealth(callback: (payload: string) => void): void;
  translateText(payload: string, callback: (payload: string) => void): void;
  previewRemoteCalls(payload: string, callback: (payload: string) => void): void;
  listHistory(callback: (payload: string) => void): void;
  getTermbase(callback: (payload: string) => void): void;
  saveProviderSettings(payload: string, callback: (payload: string) => void): void;
  smokeProviders(payload: string, callback: (payload: string) => void): void;
}

declare global {
  interface Window {
    consensusTranslationBridge?: QtContractBridge;
  }
}

function parseBridgePayload<T>(payload: string): T {
  return JSON.parse(payload) as T;
}

export function is_backend_bridge_available(): boolean {
  return Boolean(window.consensusTranslationBridge);
}

export function get_capabilities_from_backend(): Promise<CapabilityMap> {
  return new Promise((resolve, reject) => {
    const bridge = window.consensusTranslationBridge;
    if (!bridge) {
      reject(new Error("backend contract bridge unavailable"));
      return;
    }
    bridge.getCapabilities((payload) => resolve(parseBridgePayload<CapabilityMap>(payload)));
  });
}

export function get_self_decision_status(): Promise<SelfDecisionStatusDTO> {
  return new Promise((resolve, reject) => {
    const bridge = window.consensusTranslationBridge;
    if (!bridge) {
      reject(new Error("backend contract bridge unavailable"));
      return;
    }
    bridge.getSelfDecisionStatus((payload) => resolve(parseBridgePayload<SelfDecisionStatusDTO>(payload)));
  });
}

export function get_provider_health(): Promise<ProviderHealthDTO[]> {
  return new Promise((resolve, reject) => {
    const bridge = window.consensusTranslationBridge;
    if (!bridge) {
      reject(new Error("backend contract bridge unavailable"));
      return;
    }
    bridge.getProviderHealth((payload) => resolve(parseBridgePayload<ProviderHealthDTO[]>(payload)));
  });
}

export function translate_text(request: TranslationRequestDTO): Promise<TranslationResultDTO> {
  return new Promise((resolve, reject) => {
    const bridge = window.consensusTranslationBridge;
    if (!bridge) {
      reject(new Error("backend contract bridge unavailable"));
      return;
    }
    bridge.translateText(JSON.stringify(request), (payload) => resolve(parseBridgePayload<TranslationResultDTO>(payload)));
  });
}

export function preview_remote_calls(request: TranslationRequestDTO): Promise<{ ok: boolean; lines: string[] }> {
  return new Promise((resolve, reject) => {
    const bridge = window.consensusTranslationBridge;
    if (!bridge) {
      reject(new Error("backend contract bridge unavailable"));
      return;
    }
    bridge.previewRemoteCalls(JSON.stringify(request), (payload) => resolve(parseBridgePayload<{ ok: boolean; lines: string[] }>(payload)));
  });
}

export interface HistoryRecordDTO {
  id: string;
  source_text: string;
  translated_text: string;
  source_language: string;
  target_language: string;
  topic: string;
  mode: string;
  run_id: string;
  workflow_status: string;
  consensus_score: number | null;
  confidence_level: string;
  conflicts: string[];
  arbitration_reason: string;
  requires_human_review: boolean;
  rating: number | null;
}

export type TermbaseDTO = Record<string, Record<string, string>>;

export interface ProviderSettingsRequestDTO {
  provider_id: string;
  base_url: string;
  model: string;
  api_key: string;
  estimated_cost: number;
  enabled: boolean;
}

export function list_history(): Promise<HistoryRecordDTO[]> {
  return new Promise((resolve, reject) => {
    const bridge = window.consensusTranslationBridge;
    if (!bridge) {
      reject(new Error("backend contract bridge unavailable"));
      return;
    }
    bridge.listHistory((payload) => resolve(parseBridgePayload<HistoryRecordDTO[]>(payload)));
  });
}

export function get_termbase(): Promise<TermbaseDTO> {
  return new Promise((resolve, reject) => {
    const bridge = window.consensusTranslationBridge;
    if (!bridge) {
      reject(new Error("backend contract bridge unavailable"));
      return;
    }
    bridge.getTermbase((payload) => resolve(parseBridgePayload<TermbaseDTO>(payload)));
  });
}

export function save_provider_settings(request: ProviderSettingsRequestDTO): Promise<{ ok: boolean; provider_id: string }> {
  return new Promise((resolve, reject) => {
    const bridge = window.consensusTranslationBridge;
    if (!bridge) {
      reject(new Error("backend contract bridge unavailable"));
      return;
    }
    bridge.saveProviderSettings(JSON.stringify(request), (payload) => resolve(parseBridgePayload<{ ok: boolean; provider_id: string }>(payload)));
  });
}

export function smoke_providers(sample_text: string): Promise<{ ok: boolean; lines: string[] }> {
  return new Promise((resolve, reject) => {
    const bridge = window.consensusTranslationBridge;
    if (!bridge) {
      reject(new Error("backend contract bridge unavailable"));
      return;
    }
    bridge.smokeProviders(JSON.stringify({ sample_text }), (payload) => resolve(parseBridgePayload<{ ok: boolean; lines: string[] }>(payload)));
  });
}
