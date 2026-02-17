import { app, HttpRequest, HttpResponseInit, InvocationContext } from '@azure/functions';
import { CosmosClient } from '@azure/cosmos';
import { BlobServiceClient } from '@azure/storage-blob';
import { requireEnv, jsonResponse, extractUserInfo, DEFAULT_LIMIT, MAX_LIMIT, PRESIGNED_URL_EXPIRY, CORS_HEADERS, PROFILE_DOC_TYPE } from '../common';
import type { Post, PostDocument, ListPostsResponse } from '../types';

const cosmosClient = new CosmosClient({
  endpoint: requireEnv('COSMOS_DB_ENDPOINT'),
  key: requireEnv('COSMOS_DB_KEY'),
});

const blobServiceClient = BlobServiceClient.fromConnectionString(
  `DefaultEndpointsProtocol=https;AccountName=${requireEnv('STORAGE_ACCOUNT_NAME')};AccountKey=${requireEnv('STORAGE_ACCOUNT_KEY')};EndpointSuffix=core.windows.net`
);

async function generateSasUrl(containerName: string, blobName: string): Promise<string> {
  const containerClient = blobServiceClient.getContainerClient(containerName);
  const blobClient = containerClient.getBlobClient(blobName);
  
  const expiresOn = new Date();
  expiresOn.setSeconds(expiresOn.getSeconds() + PRESIGNED_URL_EXPIRY);
  
  // For public blobs, just return the URL
  return blobClient.url;
}

export async function listPosts(
  request: HttpRequest,
  context: InvocationContext
): Promise<HttpResponseInit> {
  try {
    if (request.method === 'OPTIONS') {
      return { status: 204, headers: CORS_HEADERS };
    }
    const url = new URL(request.url);
    const limitParam = url.searchParams.get('limit');
    const continuationToken = url.searchParams.get('continuationToken');
    
    const limit = limitParam ? Math.min(parseInt(limitParam, 10), MAX_LIMIT) : DEFAULT_LIMIT;

    const database = cosmosClient.database(requireEnv('COSMOS_DB_DATABASE'));
    const container = database.container(requireEnv('COSMOS_DB_CONTAINER'));
    
    const querySpec = {
      query: 'SELECT * FROM c WHERE IS_DEFINED(c.postId) ORDER BY c.createdAt DESC',
    };
    
    const { resources, continuationToken: nextToken } = await container.items
      .query(querySpec, { maxItemCount: limit, continuationToken: continuationToken || undefined })
      .fetchNext();

    const safeResources = resources ?? [];

    const containerName = requireEnv('STORAGE_IMAGES_CONTAINER');
    
    const userIds = Array.from(new Set(safeResources
      .map((doc: PostDocument) => doc.userId)
      .filter((id): id is string => !!id)));

    const nicknameByUserId = new Map<string, string>();
    if (userIds.length > 0) {
      const placeholders = userIds.map((_, index) => `@uid${index}`).join(', ');
      const profileQuery = {
        query: `SELECT c.userId, c.nickname FROM c WHERE c.docType = @docType AND c.userId IN (${placeholders})`,
        parameters: [
          { name: '@docType', value: PROFILE_DOC_TYPE },
          ...userIds.map((id, index) => ({ name: `@uid${index}`, value: id })),
        ],
      };
      const { resources: profileDocs } = await container.items.query(profileQuery).fetchAll();
      (profileDocs ?? []).forEach((doc: { userId?: string; nickname?: string }) => {
        const nickname = doc.nickname?.trim();
        if (doc.userId && nickname) {
          nicknameByUserId.set(doc.userId, nickname);
        }
      });
    }

    // Generate SAS URLs for images
    const items: Post[] = await Promise.all(
      safeResources.map(async (doc: PostDocument) => {
        const post: Post = {
          postId: doc.postId,
          userId: doc.userId,
          content: doc.content,
          createdAt: doc.createdAt,
          ...(doc.nickname && { nickname: doc.nickname }),
          ...(doc.tags && { tags: doc.tags }),
        };

        const profileNickname = nicknameByUserId.get(doc.userId);
        if (profileNickname) {
          post.nickname = profileNickname;
        }

        if (doc.imageKeys && doc.imageKeys.length > 0) {
          post.imageUrls = await Promise.all(
            doc.imageKeys.map(key => generateSasUrl(containerName, key))
          );
        }

        return post;
      })
    );

    const response: ListPostsResponse = {
      items,
      limit,
      ...(nextToken && { continuationToken: nextToken }),
    };

    return jsonResponse(200, response);
  } catch (error) {
    context.error('Error listing posts:', error);
    return jsonResponse(500, { message: 'Internal server error' });
  }
}

app.http('listPosts', {
  methods: ['GET', 'OPTIONS'],
  authLevel: 'anonymous',
  route: 'listposts',
  handler: listPosts,
});
