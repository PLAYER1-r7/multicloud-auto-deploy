/**
 * アプリケーション全体で使用する定数を定義
 */

const requiredEnv = (key: keyof ImportMetaEnv): string => {
  const value = import.meta.env[key];
  if (!value) {
    throw new Error(`Missing required environment variable: ${key}`);
  }
  return value;
};

// API設定
export const API_CONFIG = {
  BASE_URL: requiredEnv('VITE_API_URL'),
  PROFILE_URL: import.meta.env.VITE_API_PROFILE_URL || '',
  TIMEOUT: 30000, // 30秒
} as const;

// Cognito設定
export const COGNITO_CONFIG = {
  DOMAIN: requiredEnv('VITE_COGNITO_DOMAIN'),
  CLIENT_ID: requiredEnv('VITE_COGNITO_CLIENT_ID'),
  REGION: 'ap-northeast-1',
  USER_POOL_ID: requiredEnv('VITE_USER_POOL_ID'),
  REDIRECT_URI: requiredEnv('VITE_REDIRECT_URI'),
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

// 期待されるトークン発行者
export const EXPECTED_ISSUER = 
  `https://cognito-idp.${COGNITO_CONFIG.REGION}.amazonaws.com/${COGNITO_CONFIG.USER_POOL_ID}`;
