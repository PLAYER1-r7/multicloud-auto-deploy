export interface Post {
  postId: string;
  userId: string;
  nickname?: string | null;
  content: string;
  isMarkdown: boolean;
  tags: string[];
  imageUrls?: string[] | null;
  createdAt: string;
  updatedAt?: string | null;
}

export interface PostsResponse {
  items: Post[];
  total: number;
  nextToken?: string | null;
  limit: number;
}

export interface CreatePostInput {
  content: string;
  tags?: string[];
  is_markdown?: boolean;
}

export interface UpdatePostInput {
  content?: string;
  tags?: string[];
  is_markdown?: boolean;
}
