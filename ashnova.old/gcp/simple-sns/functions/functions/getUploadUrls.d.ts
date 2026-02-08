import type { Request, Response } from '@google-cloud/functions-framework';
/**
 * Cloud Function: Get Upload URLs
 * GET /api/upload-urls?count=3
 */
export declare function getUploadUrls(req: Request, res: Response): Promise<void>;
