/**
 * アプリケーション全体で使用する定数を定義
 */

// API設定
export const API_CONFIG = {
  BASE_URL: import.meta.env.VITE_API_BASE || 
    'https://1y5w2smpb4.execute-api.ap-northeast-1.amazonaws.com/prod',
  PROFILE_URL: import.meta.env.VITE_API_PROFILE_URL || '',
  TIMEOUT: 30000, // 30秒
} as const;

// Cognito設定
export const COGNITO_CONFIG = {
  DOMAIN: import.meta.env.VITE_COGNITO_DOMAIN || 
    'https://simple-sns-2026-kr070001.auth.ap-northeast-1.amazoncognito.com',
  CLIENT_ID: import.meta.env.VITE_COGNITO_CLIENT_ID || 
    '34t49tr84ufqq77flj8uspumck',
  REGION: 'ap-northeast-1',
  USER_POOL_ID: 'ap-northeast-1_lLb8qq7Rq',
  REDIRECT_URI: import.meta.env.VITE_REDIRECT_URI || window.location.origin + '/',
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
