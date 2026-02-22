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
  imageKeys?: string[];
}

export interface UpdatePostInput {
  content?: string;
  tags?: string[];
  is_markdown?: boolean;
}

export interface PresignedUrl {
  url: string;
  key: string;
}

export interface PresignedUrlsResponse {
  urls: PresignedUrl[];
}

export interface Profile {
  userId: string;
  nickname?: string | null;
  bio?: string | null;
  avatarUrl?: string | null;
}
