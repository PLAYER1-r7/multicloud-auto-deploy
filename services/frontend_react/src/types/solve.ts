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

// ── 図示データ ──────────────────────────────────────
export interface PlotCurve {
  type: "parametric" | "function";
  /** mathjs 互換式 (t の関数) */
  x?: string;
  y?: string;
  /** mathjs 互換式 (x の関数) */
  fn?: string;
  tMin?: number;
  tMax?: number;
  label?: string;
}

export interface PlotPoint {
  x: number;
  y: number;
  label?: string;
}

export interface PlotSegment {
  from: [number, number];
  to: [number, number];
  label?: string;
}

export interface PlotViewBox {
  xMin: number;
  xMax: number;
  yMin: number;
  yMax: number;
}

// ── 3D 図示データ ────────────────────────────────────
export interface PlotPoint3D {
  x: number;
  y: number;
  z: number;
  label?: string;
}

export interface PlotLine3D {
  from: [number, number, number];
  to: [number, number, number];
  label?: string;
}

export interface PlotPlane3D {
  /** ax + by + cz = d */
  a: number;
  b: number;
  c: number;
  d: number;
  xRange: [number, number];
  yRange: [number, number];
  label?: string;
}

export interface PlotSurface3D {
  /** mathjs 互換式 z = f(x, y) */
  fnZ: string;
  xRange: [number, number];
  yRange: [number, number];
  label?: string;
}

export interface PlotViewRange3D {
  xRange: [number, number];
  yRange: [number, number];
  zRange: [number, number];
}

export interface PlotData {
  needPlot: boolean;
  /** 2 = 2D (default), 3 = 3D */
  dimension?: number;
  curves: PlotCurve[];
  segments?: PlotSegment[];
  points?: PlotPoint[];
  viewBox?: PlotViewBox;
  /** 3D data */
  points3d?: PlotPoint3D[];
  lines3d?: PlotLine3D[];
  planes3d?: PlotPlane3D[];
  surfaces3d?: PlotSurface3D[];
  viewRange3d?: PlotViewRange3D;
}

// ── 解答・レスポンス ────────────────────────────────
export interface SolveAnswer {
  final: string;
  latex?: string;
  steps: string[];
  diagramGuide?: string;
  plotData?: PlotData;
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
