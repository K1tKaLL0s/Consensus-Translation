import type { TaskStatus } from "./task_status";
import type { ErrorCode } from "./error_code";

export type FinalizeEventType =
  | "translation_finalize"
  | "learning_finalize"
  | "review_confirm"
  | "store_commit"
  | "rating_submit"
  | "rating_skip";

export interface FinalizeEventDTO {
  event_type: FinalizeEventType;
  task_status: TaskStatus;
  run_id: string;
  error_code: ErrorCode;
  metadata: Record<string, unknown>;
}

export function finalize_event(
  event_type: FinalizeEventType,
  task_status: TaskStatus,
  run_id = "",
  metadata: Record<string, unknown> = {},
): FinalizeEventDTO {
  return {
    event_type,
    task_status,
    run_id,
    error_code: "none",
    metadata,
  };
}

