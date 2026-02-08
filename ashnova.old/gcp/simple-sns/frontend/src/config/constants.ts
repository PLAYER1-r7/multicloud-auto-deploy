export const API_CONFIG = {
  BASE_URL: import.meta.env.VITE_API_BASE_URL || 'https://YOUR-REGION-YOUR-PROJECT.cloudfunctions.net',
  LIST_POSTS_URL: import.meta.env.VITE_API_LIST_POSTS_URL || '',
  CREATE_POST_URL: import.meta.env.VITE_API_CREATE_POST_URL || '',
  DELETE_POST_URL: import.meta.env.VITE_API_DELETE_POST_URL || '',
  UPLOAD_URLS_URL: import.meta.env.VITE_API_UPLOAD_URLS_URL || '',
  PROFILE_URL: import.meta.env.VITE_API_PROFILE_URL || '',
  TIMEOUT: 30000, // 30秒
} as const;

// Firebase設定（GCP版ではCognitoの代わりにFirebaseを使用）
export const FIREBASE_CONFIG = {
  API_KEY: import.meta.env.VITE_FIREBASE_API_KEY || '',
  AUTH_DOMAIN: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN || '',
  PROJECT_ID: import.meta.env.VITE_FIREBASE_PROJECT_ID || '',
  STORAGE_BUCKET: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET || '',
  APP_ID: import.meta.env.VITE_FIREBASE_APP_ID || '',
} as const;

// レート制限設定
export const RATE_LIMIT_CONFIG = {
  MAX_REQUESTS: 100,
  TIME_WINDOW: 60000, // 1分
} as const;

// ページネーション設定
export const PAGINATION_CONFIG = {
  DEFAULT_PAGE_SIZE: 20,
  PAGE_SIZE_OPTIONS: [10, 20, 50] as const,
  STORAGE_KEY: 'pageSize',
} as const;

// 投稿設定
export const POST_CONFIG = {
  MAX_CONTENT_LENGTH: 5000,
  MIN_CONTENT_LENGTH: 1,
  MAX_IMAGE_SIZE: 5 * 1024 * 1024, // 5MB
  ALLOWED_IMAGE_TYPES: ['image/jpeg', 'image/png', 'image/gif', 'image/webp'] as const,
} as const;

// プロフィール設定
export const PROFILE_CONFIG = {
  MIN_NICKNAME_LENGTH: 1,
  MAX_NICKNAME_LENGTH: 50,
} as const;

// ローカルストレージキー
export const STORAGE_KEYS = {
  ID_TOKEN: 'id_token',
  ACCESS_TOKEN: 'access_token',
  REFRESH_TOKEN: 'refresh_token',
  PAGE_SIZE: 'pageSize',
} as const;

export const APP_CONFIG = {
  MAX_IMAGES_PER_POST: 5,
  MAX_TAGS_PER_POST: 10,
  MAX_CONTENT_LENGTH: 5000,
};
