import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import { apiFetch } from '../services/api';
import { listPostsResponseSchema, type Post } from '../utils/validation';

/**
 * Fetch posts from API
 */
const fetchPosts = async (limit: number = 20, nextToken?: string, tag?: string): Promise<{ items: Post[]; nextToken?: string }> => {
  const params = new URLSearchParams({ limit: String(limit) });
  if (nextToken) {
    params.append('continuationToken', nextToken);
  }
  if (tag && tag.trim()) {
    params.append('tag', tag.trim());
  }

  const { res, json } = await apiFetch(`/listposts?${params.toString()}`, {
    method: 'GET',
  });

  if (!res.ok) {
    throw new Error(`Failed to fetch posts: ${res.status} ${res.statusText}`);
  }

  const validated = listPostsResponseSchema.parse(json);
  console.log('Posts fetched:', validated.items.length, 'posts');
  console.log('Sample post tags:', validated.items[0]?.tags);
  return { items: validated.items, nextToken: validated.nextToken ?? validated.continuationToken };
};

/**
 * Get upload URLs for S3 presigned upload
 */
const getUploadUrls = async (count: number): Promise<{ urls: Array<{ url: string; key: string }> }> => {
  const params = new URLSearchParams({ count: String(count) });
  const { res, json } = await apiFetch(`/upload-urls?${params.toString()}`, {
    method: 'GET',
  });

  if (!res.ok) {
    const errorMessage = json?.message || json?.error || `Failed to get upload URLs: ${res.status}`;
    throw new Error(errorMessage);
  }
  
  return {
    urls: (json?.uploadUrls ?? []).map((item: { key: string; uploadUrl: string }) => ({
      key: item.key,
      url: item.uploadUrl,
    })),
  };
};

/**
 * Upload image to S3 using presigned URL
 */
const uploadToS3 = async (url: string, blob: Blob): Promise<void> => {
  const res = await fetch(url, {
    method: 'PUT',
    body: blob,
    headers: {
      'Content-Type': 'image/jpeg',
      'x-ms-blob-type': 'BlockBlob',
      'x-ms-blob-content-type': 'image/jpeg',
    },
  });

  if (!res.ok) {
    throw new Error(`Failed to upload to S3: ${res.status}`);
  }
};

/**
 * Create a new post
 */
const createPost = async (data: { content: string; imageKeys?: string[]; tags?: string[] }): Promise<void> => {
  const { res, json } = await apiFetch('/posts', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });

  if (!res.ok) {
    const errorMessage = json?.message || json?.error || `Failed to create post: ${res.status}`;
    throw new Error(errorMessage);
  }
  
  // Success - json contains { item: {...} }
};

/**
 * Delete a post
 */
const deletePost = async (postId: string): Promise<void> => {
  const { res, json } = await apiFetch(`/posts/${postId}`, {
    method: 'DELETE',
  });

  if (!res.ok) {
    throw new Error(json?.message || `Failed to delete post: ${res.status}`);
  }
};

/**
 * Hook to get upload URLs
 */
export const useGetUploadUrls = () => {
  return useMutation({
    mutationFn: getUploadUrls,
    onError: (error: Error) => {
      console.error('Get upload URLs error:', error);
      toast.error(error.message || 'アップロードURLの取得に失敗しました');
    },
  });
};

/**
 * Hook to upload to S3
 */
export const useUploadToS3 = () => {
  return useMutation({
    mutationFn: ({ url, blob }: { url: string; blob: Blob }) => uploadToS3(url, blob),
    onError: (error: Error) => {
      console.error('S3 upload error:', error);
      toast.error('画像のアップロードに失敗しました');
    },
  });
};

/**
 * Hook to fetch posts with pagination
 */
export const usePosts = (limit: number = 20, nextToken?: string, tag?: string) => {
  return useQuery({
    queryKey: ['posts', limit, nextToken, tag],
    queryFn: () => fetchPosts(limit, nextToken, tag),
    staleTime: 30000, // 30 seconds
    refetchOnWindowFocus: true,
  });
};

/**
 * Hook to create a post
 */
export const useCreatePost = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: createPost,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['posts'] });
      toast.success('投稿しました');
    },
    onError: (error: Error) => {
      toast.error(error.message || '投稿に失敗しました');
    },
  });
};

/**
 * Hook to delete a post
 */
export const useDeletePost = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: deletePost,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['posts'] });
      toast.success('投稿を削除しました');
    },
    onError: (error: Error) => {
      toast.error(error.message || '削除に失敗しました');
    },
  });
};
