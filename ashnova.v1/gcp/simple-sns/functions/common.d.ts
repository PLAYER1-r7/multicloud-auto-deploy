import type { Request, Response } from '@google-cloud/functions-framework';
import * as admin from 'firebase-admin';
export declare const db: admin.firestore.Firestore;
export declare const storage: import("firebase-admin/lib/storage/storage").Storage;
export declare const MAX_IMAGES_PER_POST = 5;
export declare const MAX_TAGS_PER_POST = 10;
export declare const MAX_CONTENT_LENGTH = 5000;
export declare const SAS_URL_EXPIRY_MINUTES = 5;
export interface UserInfo {
    userId: string;
    email?: string;
}
/**
 * Extract user info from Firebase Auth token
 */
export declare function extractUserInfo(req: Request): Promise<UserInfo | null>;
/**
 * JSON response helper
 */
export declare function jsonResponse(res: Response, statusCode: number, data: any): void;
/**
 * CORS headers - Allow all origins for simplicity
 */
export declare function setCorsHeaders(res: Response, req?: Request): void;
/**
 * Handle OPTIONS requests for CORS
 */
export declare function handleCorsOptions(req: Request, res: Response): boolean;
/**
 * Require environment variable
 */
export declare function requireEnv(name: string): string;
