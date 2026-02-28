/** PHASE 2 & 3 Learning API クライアント */

import apiClient from "./client";
import type {
  CreateMaterialFromSolveRequest,
  EnhancedLearningMaterial,
  AudioResponse,
  RecommendationResponse,
  LearningProfile,
} from "../types/learning";

export interface CreatedMaterialResponse {
  materialId?: string;
  material_id?: string;
  createdAt?: string;
  created_at?: string;
}

// ── Base API endpoints ─────────────────────────────────

/**
 * 教材を生成（PHASE 1）
 * POST /v1/learn/materials/from-solve
 */
export const createMaterialFromSolve = async (
  request: CreateMaterialFromSolveRequest,
): Promise<CreatedMaterialResponse> => {
  const response = await apiClient.post(
    "/v1/learn/materials/from-solve",
    request,
  );
  return response.data as CreatedMaterialResponse;
};

const normalizeAudioResponse = (data: unknown): AudioResponse => {
  const payload = (data ?? {}) as Record<string, unknown>;
  return {
    material_id:
      (payload.material_id as string | undefined) ??
      (payload.materialId as string | undefined) ??
      "",
    audio_urls:
      (payload.audio_urls as Record<string, string> | undefined) ??
      (payload.audioUrls as Record<string, string> | undefined) ??
      {},
    audio_format:
      (payload.audio_format as "mp3" | "wav" | undefined) ??
      (payload.audioFormat as "mp3" | "wav" | undefined) ??
      "mp3",
    generated_at:
      (payload.generated_at as string | undefined) ??
      (payload.generatedAt as string | undefined) ??
      new Date().toISOString(),
  };
};

/**
 * Bedrock で教材を拡張（PHASE 2）
 * POST /v1/learn/materials/{material_id}/enhance
 */
export const enhanceMaterial = async (
  materialId: string,
): Promise<EnhancedLearningMaterial> => {
  const response = await apiClient.post(
    `/v1/learn/materials/${materialId}/enhance`,
  );
  return response.data;
};

/**
 * Polly で音声を生成（PHASE 2）
 * POST /v1/learn/materials/{material_id}/audio
 */
export const generateAudio = async (
  materialId: string,
): Promise<AudioResponse> => {
  const response = await apiClient.post(
    `/v1/learn/materials/${materialId}/audio`,
  );
  return normalizeAudioResponse(response.data);
};

/**
 * Personalize で推薦を取得（PHASE 2）
 * GET /v1/learn/users/{user_id}/recommendations
 */
export const getRecommendations = async (
  userId: string,
  numResults: number = 5,
): Promise<RecommendationResponse> => {
  const response = await apiClient.get(
    `/v1/learn/users/${userId}/recommendations`,
    {
      params: { num_results: numResults },
    },
  );
  return response.data;
};

/**
 * 教材を完全に拡張（PHASE 2 フルパイプライン）
 * POST /v1/learn/materials/{material_id}/enhance/full
 */
export const enhanceMaterialFull = async (
  materialId: string,
): Promise<{
  material: EnhancedLearningMaterial;
  audio: AudioResponse;
  recommendations: RecommendationResponse;
}> => {
  const response = await apiClient.post(
    `/v1/learn/materials/${materialId}/enhance/full`,
  );
  return response.data;
};

/**
 * ユーザーの学習パターンを分析（PHASE 2）
 * POST /v1/learn/users/{user_id}/analyze-pattern
 */
export const analyzeLearningPattern = async (
  userId: string,
  materialIds: string[],
): Promise<LearningProfile> => {
  const response = await apiClient.post(
    `/v1/learn/users/${userId}/analyze-pattern`,
    {
      material_ids: materialIds,
    },
  );
  return response.data;
};

/**
 * ユーザーのインタラクションを記録（PHASE 2）
 * POST /v1/learn/users/{user_id}/interactions
 */
export const trackInteraction = async (
  userId: string,
  materialId: string,
  interactionType: "view" | "complete" | "bookmark" | "struggle",
): Promise<{ status: string }> => {
  const response = await apiClient.post(
    `/v1/learn/users/${userId}/interactions`,
    {
      material_id: materialId,
      interaction_type: interactionType,
      timestamp: new Date().toISOString(),
    },
  );
  return response.data;
};
