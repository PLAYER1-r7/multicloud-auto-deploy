import type { Request, Response } from '@google-cloud/functions-framework';
/**
 * Cloud Function: Delete Post
 * DELETE /api/posts/:postId
 */
export declare function deletePost(req: Request, res: Response): Promise<void>;
