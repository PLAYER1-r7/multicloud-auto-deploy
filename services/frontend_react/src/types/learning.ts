/** PHASE 2 & 3 用の型定義 */

// ── Learning Material Types ────────────────────────────────
export interface LearningOutlineStep {
  stepNumber: number;
  brief: string;
  details: string;
  keyFormula?: string;
}

export interface QuizQuestion {
  questionId: string;
  questionType: "short_answer" | "fill_blank" | "multiple_choice";
  questionText: string;
  options?: string[];
  answer: string;
  explanation: string;
}

export interface CommonMistake {
  mistakeDescription: string;
  whyWrong: string;
  correction: string;
  preventionTip: string;
}

export interface ReferenceProblem {
  university: string;
  year: number;
  questionNo: string;
  similarityScore: number;
}

export interface ExamMetadata {
  university: string;
  year: number;
  subject: string;
  questionNo?: string;
}

export interface LearningMaterial {
  materialId: string;
  createdAt: string;
  sourceSolveResponseId?: string;
  examMetadata: ExamMetadata;
  problemText: string;
  problemImageUrl?: string;
  solutionFinal: string;
  solutionSteps: string[];
  solutionLatex: string;
  solutionConfidence: number;
  ocrProvider: string;
  outline: LearningOutlineStep[];
  keyConcepts: string[];
  quizQuestions: QuizQuestion[];
  commonMistakes: CommonMistake[];
  additionalExamples: string[];
  referenceProblems: ReferenceProblem[];
  difficultyLevel: "basic" | "intermediate" | "advanced";
  learningObjectives: string[];
  awsPersonalizationScore: number;
}

// ── Enhanced Material Types (PHASE 2) ────────────────────────────
export interface EnhancedLearningMaterial {
  baseMaterial: LearningMaterial;
  detailedExplanation: string;
  conceptDeepDives: Record<string, string>;
  mistakeAnalysis: string[];
  audioUrls: Record<string, string>;
  personalizedRecommendations: string[];
  personalizationScore: number;
  enhancementModels: Record<string, string>;
  isFullyEnhanced: boolean;
}

// ── Audio Generation Types ─────────────────────────────
export interface AudioResponse {
  material_id: string;
  audio_urls: Record<string, string>;
  audio_format: "mp3" | "wav";
  generated_at: string;
}

export interface AudioResponseCamel {
  materialId: string;
  audioUrls: Record<string, string>;
  audioFormat: "mp3" | "wav";
  generatedAt: string;
}

export type AudioResponseLike = AudioResponse | AudioResponseCamel;

// ── Personalization Types ──────────────────────────────
export interface LearningProfile {
  preferred_difficulty: "basic" | "intermediate" | "advanced";
  preferred_concepts: string[];
  learning_speed: "slow" | "normal" | "fast";
  materials_completed: number;
}

export interface Recommendation {
  material_id: string;
  score: number;
}

export interface RecommendationResponse {
  user_id: string;
  recommendations: Recommendation[];
  learning_profile: LearningProfile;
}

// ── API Request/Response Types ─────────────────────────────
export interface CreateMaterialFromSolveRequest {
  solve_response: {
    request_id: string;
    status: "success" | "error";
    problem_text: string;
    answer: {
      final: string;
      latex: string;
      steps: string[];
      confidence: number;
    };
    meta: {
      ocr_provider: string;
      model: string;
      latency_ms: number;
      cost_usd: number;
    };
  };
  exam: ExamMetadata;
  problem_image_url?: string;
}

export interface EnhanceResponse {
  baseMaterial: LearningMaterial;
  detailedExplanation: string;
  conceptDeepDives: Record<string, string>;
  mistakeAnalysis: string[];
  enhancementModels: Record<string, string>;
}
