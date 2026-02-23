import apiClient from "./client";

export interface ServiceLimits {
  maxImagesPerPost: number;
}

/** バックエンドからサービス制限値を取得する */
export async function fetchLimits(): Promise<ServiceLimits> {
  const res = await apiClient.get<ServiceLimits>("/limits");
  return res.data;
}
