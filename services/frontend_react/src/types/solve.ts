/** API の SolveRequest / SolveResponse に対応する TypeScript 型定義 */

export interface SolveInput {
  imageBase64?: string;
  imageUrl?: string;
  source: "paste" | "upload" | "url";
}

export interface SolveExam {
  university: string;
  year: number;
  subject: string;
  questionNo?: string;
}

export interface SolveOptions {
  mode?: "fast" | "accurate";
  needSteps?: boolean;
  needLatex?: boolean;
  maxTokens?: number;
  debugOcr?: boolean;
}

export interface SolveRequest {
  input: SolveInput;
  exam: SolveExam;
  options?: SolveOptions;
}

export interface SolveAnswer {
  final: string;
  latex?: string;
  steps: string[];
  diagramGuide?: string;
  confidence: number;
}

export interface SolveMeta {
  ocrProvider: string;
  ocrSource?: string;
  ocrScore?: number;
  ocrCandidates?: number;
  model: string;
  latencyMs: number;
  costUsd: number;
}

export interface SolveResponse {
  requestId: string;
  status: string;
  problemText: string;
  answer: SolveAnswer;
  meta: SolveMeta;
}
