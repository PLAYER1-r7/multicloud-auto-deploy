export interface Post {
  postId: string;
  userId: string;
  nickname?: string; // User's display name from Cognito
  content: string;
  createdAt: string;
  imageUrl?: string; // Signed S3 URL from backend (deprecated, use imageUrls)
  imageUrls?: string[]; // Multiple signed S3 URLs (max 16)
  tags?: string[]; // Tags for categorization and search
}

export interface VersionInfo {
  currentVersion: string;
  releaseDate: string;
  releaseNotesUrl: string;
  latestReleaseUrl: string;
  changes?: string[]; // List of changes in this version
}

export interface AuthUser {
  sub: string;
  email?: string;
}

export interface UserProfile {
  userId: string;
  nickname?: string;
  updatedAt?: string;
  createdAt?: string;
}

export interface UploadUrlResponse {
  postId: string;
  urls: Array<{
    url: string;
    key: string;
  }>;
  expiresIn: number;
}
