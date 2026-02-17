export interface Post {
  postId: string;
  userId: string;
  nickname?: string;
  content: string;
  createdAt: string;
  imageUrls?: string[];
  tags?: string[];
}

export interface PostDocument extends Post {
  id: string;
  imageKeys?: string[];
  docType?: string;
}

export interface CreatePostBody {
  content?: string;
  imageKeys?: string[];
  tags?: string[];
}

export interface ListPostsResponse {
  items: Post[];
  limit: number;
  continuationToken?: string;
}

export interface ErrorResponse {
  message: string;
  details?: unknown;
}

export interface UserInfo {
  userId: string;
  email?: string;
  name?: string;
}

export interface UserProfile {
  userId: string;
  nickname?: string;
  updatedAt?: string;
  createdAt?: string;
}
