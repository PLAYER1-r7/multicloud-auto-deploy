import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { postsApi } from '../api/client';
import type { CreatePostInput, UpdatePostInput } from '../types/message';

// Query keys
const POSTS_KEY = ['posts'] as const;

// 投稿一覧フック（カーソルページネーション）
export function usePosts(limit: number = 20, nextToken?: string | null, tag?: string | null) {
  return useQuery({
    queryKey: [...POSTS_KEY, limit, nextToken, tag],
    queryFn: () => postsApi.getPosts(limit, nextToken, tag),
    staleTime: 30000,
  });
}

// 単一投稿フック
export function usePost(postId: string) {
  return useQuery({
    queryKey: [...POSTS_KEY, postId],
    queryFn: () => postsApi.getPost(postId),
    enabled: !!postId,
  });
}

// 投稿作成フック
export function useCreatePost() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: CreatePostInput) => postsApi.createPost(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: POSTS_KEY });
    },
  });
}

// 投稿更新フック
export function useUpdatePost() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ postId, data }: { postId: string; data: UpdatePostInput }) =>
      postsApi.updatePost(postId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: POSTS_KEY });
    },
  });
}

// 投稿削除フック
export function useDeletePost() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (postId: string) => postsApi.deletePost(postId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: POSTS_KEY });
    },
  });
}

// 後方互換エイリアス（既存コードが残っている場合用）
export const useMessages = usePosts;
export const useCreateMessage = useCreatePost;
export const useUpdateMessage = useUpdatePost;
export const useDeleteMessage = useDeletePost;
