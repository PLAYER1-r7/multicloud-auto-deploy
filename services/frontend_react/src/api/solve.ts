import axios from "axios";
import type { SolveRequest, SolveResponse } from "../types/solve";

// VITE_API_URL: backend API base。空文字の場合は Vite dev proxy 経由
const API_URL = import.meta.env.VITE_API_URL ?? "";

/** solve 専用 axios インスタンス: タイムアウトを 120s に延長 */
const solveClient = axios.create({
  baseURL: API_URL,
  headers: { "Content-Type": "application/json" },
  timeout: 120_000,
});

/**
 * POST /v1/solve — 数学問題を OCR + AI 解答
 */
export async function solveMath(request: SolveRequest): Promise<SolveResponse> {
  const res = await solveClient.post<SolveResponse>("/v1/solve", request);
  return res.data;
}
