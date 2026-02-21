import apiClient from './client';
import type { Post, PostsResponse, CreatePostInput, UpdatePostInput } from '../types/message';

export const postsApi = {
  async getPosts(
    limit = 20,
    nextToken?: string | null,
    tag?: string | null,
  ): Promise<PostsResponse> {
    const res = await apiClient.get<PostsResponse>('/posts', {
      params: {
        limit,
        ...(nextToken ? { next_token: nextToken } : {}),
        ...(tag ? { tag } : {}),
      },
    });
    return res.data;
  },

  async getPost(postId: string): Promise<Post> {
    const res = await apiClient.get<Post>(`/posts/${postId}`);
    return res.data;
  },

  async createPost(data: CreatePostInput): Promise<Post> {
    const res = await apiClient.post<Post>('/posts', data);
    return res.data;
  },

  async updatePost(postId: string, data: UpdatePostInput): Promise<Post> {
    const res = await apiClient.put<Post>(`/posts/${postId}`, data);
    return res.data;
  },

  async deletePost(postId: string): Promise<void> {
    await apiClient.delete(`/posts/${postId}`);
  },
};
