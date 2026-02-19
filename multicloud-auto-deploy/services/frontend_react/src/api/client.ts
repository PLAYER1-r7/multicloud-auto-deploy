import axios from 'axios';
import type { Post, PostsResponse, CreatePostInput, UpdatePostInput } from '../types/message';

// API URL: dev = localhost:8000, cloud = VITE_API_URL env
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const apiClient = axios.create({
  baseURL: API_URL,
  headers: { 'Content-Type': 'application/json' },
  timeout: 10000,
});

export const postsApi = {
  // 投稿一覧（カーソルページネーション）
  async getPosts(
    limit: number = 20,
    nextToken?: string | null,
    tag?: string | null,
  ): Promise<PostsResponse> {
    const response = await apiClient.get<PostsResponse>('/posts', {
      params: {
        limit,
        ...(nextToken ? { next_token: nextToken } : {}),
        ...(tag ? { tag } : {}),
      },
    });
    return response.data;
  },

  // 単一投稿取得
  async getPost(postId: string): Promise<Post> {
    const response = await apiClient.get<Post>(`/posts/${postId}`);
    return response.data;
  },

  // 投稿作成
  async createPost(data: CreatePostInput): Promise<Post> {
    const response = await apiClient.post<Post>('/posts', data);
    return response.data;
  },

  // 投稿更新
  async updatePost(postId: string, data: UpdatePostInput): Promise<Post> {
    const response = await apiClient.put<Post>(`/posts/${postId}`, data);
    return response.data;
  },

  // 投稿削除
  async deletePost(postId: string): Promise<void> {
    await apiClient.delete(`/posts/${postId}`);
  },
};

export default apiClient;
