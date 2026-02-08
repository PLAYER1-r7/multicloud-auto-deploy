import type { Request, Response } from '@google-cloud/functions-framework';
import { storage, extractUserInfo, jsonResponse, handleCorsOptions, MAX_IMAGES_PER_POST, SAS_URL_EXPIRY_MINUTES } from '../common';
import { nanoid } from 'nanoid';

/**
 * Cloud Function: Get Upload URLs
 * POST /api/upload-urls
 */
export async function getUploadUrls(req: Request, res: Response) {
  if (handleCorsOptions(req, res)) return;

  try {
    // Authentication
    const userInfo = await extractUserInfo(req);
    if (!userInfo) {
      return jsonResponse(res, 401, { message: 'Unauthorized' });
    }

    // Validation
    const bodyCount = typeof req.body?.count === 'number' ? req.body.count : undefined;
    const queryCount = parseInt(req.query.count as string) || 0;
    const count = Math.min(bodyCount || queryCount || 1, MAX_IMAGES_PER_POST);

    if (count < 1) {
      return jsonResponse(res, 400, { message: 'Count must be at least 1' });
    }

    // Generate signed URLs for upload
    const bucket = storage.bucket(process.env.STORAGE_BUCKET || 'simple-sns-gcp-images');
    const uploadUrls: { url: string; key: string }[] = [];

    for (let i = 0; i < count; i++) {
      const imageId = nanoid();
      const imageKey = `images/${userInfo.userId}/${imageId}.jpg`;
      const file = bucket.file(imageKey);

      const [uploadUrl] = await file.getSignedUrl({
        version: 'v4',
        action: 'write',
        expires: Date.now() + SAS_URL_EXPIRY_MINUTES * 60 * 1000,
        contentType: 'image/jpeg',
      });

      uploadUrls.push({ url: uploadUrl, key: imageKey });
    }

    console.log('Upload URLs generated:', { userId: userInfo.userId, count });
    return jsonResponse(res, 200, { urls: uploadUrls, expiresIn: SAS_URL_EXPIRY_MINUTES * 60 });
  } catch (error) {
    console.error('Error generating upload URLs:', error);
    return jsonResponse(res, 500, { message: 'Internal server error' });
  }
}
