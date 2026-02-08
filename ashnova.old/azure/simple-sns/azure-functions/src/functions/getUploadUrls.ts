import { app, HttpRequest, HttpResponseInit, InvocationContext } from '@azure/functions';
import { extractUserInfo, generateBlobWriteUrl, MAX_IMAGES_PER_POST } from '../common';
import { nanoid } from 'nanoid';

/**
 * Azure Function: Get Upload URLs
 * POST /api/upload-urls
 */
async function getUploadUrls(request: HttpRequest, context: InvocationContext): Promise<HttpResponseInit> {
  try {
    // Authentication
    const authHeader = request.headers.get('authorization');
    const userInfo = await extractUserInfo(authHeader || undefined);
    
    if (!userInfo) {
      return {
        status: 401,
        jsonBody: { message: 'Unauthorized' }
      };
    }

    // Parse request body
    const body: any = await request.json();
    const count = Math.min(parseInt(body.count || '1'), MAX_IMAGES_PER_POST);

    if (count < 1) {
      return {
        status: 400,
        jsonBody: { message: 'Count must be at least 1' }
      };
    }

    // Generate SAS URLs for upload
    const uploadUrls: { uploadUrl: string; imageKey: string }[] = [];

    for (let i = 0; i < count; i++) {
      const imageId = nanoid();
      const imageKey = `images/${userInfo.userId}/${imageId}.jpg`;
      const uploadUrl = generateBlobWriteUrl(imageKey);

      uploadUrls.push({ uploadUrl, imageKey });
    }

    context.log('Upload URLs generated:', { userId: userInfo.userId, count });
    
    return {
      status: 200,
      jsonBody: { uploadUrls },
      headers: {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Credentials': 'true'
      }
    };
  } catch (error) {
    context.error('Error generating upload URLs:', error);
    return {
      status: 500,
      jsonBody: { message: 'Internal server error' }
    };
  }
}

app.http('getUploadUrls', {
  methods: ['POST', 'OPTIONS'],
  authLevel: 'anonymous',
  route: 'upload-urls',
  handler: getUploadUrls
});
