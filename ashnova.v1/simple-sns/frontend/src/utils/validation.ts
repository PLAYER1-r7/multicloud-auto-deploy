import { z } from 'zod';

/**
 * Post content validation schema
 */
export const postContentSchema = z.string().min(1, '投稿内容を入力してください').max(5000, '投稿内容は5000文字以内にしてください');

/**
 * Validate post content
 */
export const validatePostContent = (content: string): string | null => {
  const result = postContentSchema.safeParse(content);
  if (!result.success) {
    return result.error.issues[0].message;
  }
  return null;
};

/**
 * Post response schema
 */
export const postSchema = z.object({
  postId: z.string(),
  userId: z.string(),
  nickname: z.string().optional(),
  content: z.string(),
  createdAt: z.string(),
  imageUrl: z.string().optional(),
  imageUrls: z.array(z.string()).optional(),
  isMarkdown: z.boolean().optional(),
  tags: z.array(z.string()).optional(),
});

export const listPostsResponseSchema = z.object({
  items: z.array(postSchema),
  limit: z.number(),
  nextToken: z.string().optional(),
});

export type Post = z.infer<typeof postSchema>;
export type ListPostsResponse = z.infer<typeof listPostsResponseSchema>;
