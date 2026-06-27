export interface ConsensusDTO {
  final_text: string;
  vote_map: Record<string, number>;
  conflicts: string[];
  arbitration_reason: string;
  alignment_level: "heuristic" | "surface" | "token" | "none";
  requires_review: boolean;
}

