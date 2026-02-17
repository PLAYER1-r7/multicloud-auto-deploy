import { app, HttpRequest, HttpResponseInit, InvocationContext } from '@azure/functions';
import { BlobServiceClient, generateBlobSASQueryParameters, BlobSASPermissions, StorageSharedKeyCredential } from '@azure/storage-blob';
import { requireEnv, jsonResponse, extractUserInfo, MAX_IMAGES_PER_POST, PRESIGNED_URL_EXPIRY, CORS_HEADERS } from '../common';
let nanoid: (() => string) | null = null;

const getNanoid = async (): Promise<() => string> => {
  if (!nanoid) {
    const { customAlphabet } = await import('nanoid');
    nanoid = customAlphabet('0123456789abcdefghijklmnopqrstuvwxyz', 21);
  }
  return nanoid;
};

export async function getUploadUrls(
  request: HttpRequest,
  context: InvocationContext
): Promise<HttpResponseInit> {
  try {
    if (request.method === 'OPTIONS') {
      return { status: 204, headers: CORS_HEADERS };
    }
    // Authentication
    const userInfo = await extractUserInfo(request);
    if (!userInfo) {
      return jsonResponse(401, { message: 'Unauthorized' });
    }

    const url = new URL(request.url);
    const countParam = url.searchParams.get('count');
    const count = countParam ? parseInt(countParam, 10) : 1;

    if (count < 1 || count > MAX_IMAGES_PER_POST) {
      return jsonResponse(400, { message: `Count must be between 1 and ${MAX_IMAGES_PER_POST}` });
    }

    const accountName = requireEnv('STORAGE_ACCOUNT_NAME');
    const accountKey = requireEnv('STORAGE_ACCOUNT_KEY');
    const containerName = requireEnv('STORAGE_IMAGES_CONTAINER');

    const sharedKeyCredential = new StorageSharedKeyCredential(accountName, accountKey);
    const blobServiceClient = new BlobServiceClient(
      `https://${accountName}.blob.core.windows.net`,
      sharedKeyCredential
    );

    const containerClient = blobServiceClient.getContainerClient(containerName);
    const uploadUrls: Array<{ key: string; uploadUrl: string }> = [];

    const expiresOn = new Date();
    expiresOn.setSeconds(expiresOn.getSeconds() + PRESIGNED_URL_EXPIRY);

    const nanoidFn = await getNanoid();
    for (let i = 0; i < count; i++) {
      const imageKey = `images/${userInfo.userId}/${nanoidFn()}.jpg`;
      const blobClient = containerClient.getBlobClient(imageKey);

      const sasToken = generateBlobSASQueryParameters(
        {
          containerName,
          blobName: imageKey,
          permissions: BlobSASPermissions.parse('cw'), // Create + Write permission
          expiresOn,
        },
        sharedKeyCredential
      ).toString();

      const uploadUrl = `${blobClient.url}?${sasToken}`;

      uploadUrls.push({ key: imageKey, uploadUrl });
    }

    context.log(`Generated ${count} upload URLs for user ${userInfo.userId}`);

    return jsonResponse(200, { uploadUrls });
  } catch (error) {
    context.error('Error generating upload URLs:', error);
    return jsonResponse(500, { message: 'Internal server error' });
  }
}

app.http('getUploadUrls', {
  methods: ['GET', 'OPTIONS'],
  authLevel: 'anonymous',
  route: 'upload-urls',
  handler: getUploadUrls,
});
