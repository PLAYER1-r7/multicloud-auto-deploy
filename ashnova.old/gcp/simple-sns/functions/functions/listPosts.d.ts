import type { Request, Response } from '@google-cloud/functions-framework';
/**
 * Cloud Function: List Posts
 * GET /api/posts?limit=20&continuationToken=...&tag=...
 */
export declare function listPosts(req: Request, res: Response): Promise<void>;
