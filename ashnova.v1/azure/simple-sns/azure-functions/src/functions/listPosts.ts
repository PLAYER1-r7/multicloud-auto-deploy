import { app, HttpRequest, HttpResponseInit, InvocationContext } from '@azure/functions';
import { getCosmosContainer, generateBlobReadUrl } from '../common';
import type { Post } from '../types';

/**
 * Azure Function: List Posts
 * GET /api/posts?limit=20&continuationToken=...&tag=...
 */
async function listPosts(request: HttpRequest, context: InvocationContext): Promise<HttpResponseInit> {
  try {
    const limit = Math.min(parseInt(request.query.get('limit') || '20'), 100);
    const tag = request.query.get('tag');
    const continuationToken = request.query.get('continuationToken');

    // Query Cosmos DB
    const container = getCosmosContainer();
    let querySpec: any = {
      query: 'SELECT * FROM c ORDER BY c.createdAt DESC OFFSET 0 LIMIT @limit',
      parameters: [
        { name: '@limit', value: limit }
      ]
    };

    // Filter by tag if provided
    if (tag) {
      querySpec = {
        query: 'SELECT * FROM c WHERE ARRAY_CONTAINS(c.tags, @tag) ORDER BY c.createdAt DESC OFFSET 0 LIMIT @limit',
        parameters: [
          { name: '@tag', value: tag },
          { name: '@limit', value: limit }
        ]
      };
    }

    // Handle continuation token
    const options: any = { maxItemCount: limit };
    if (continuationToken) {
      options.continuationToken = continuationToken;
    }

    const queryIterator = container.items.query(querySpec, options);
    const feedResponse = await queryIterator.fetchNext();
    const items = feedResponse.resources || [];
    const newToken = feedResponse.continuationToken;

    // Generate signed URLs for images
    const posts: Post[] = items.map((item: any) => {
      const post: Post = { ...item };
      delete (post as any).id; // Remove Cosmos DB id field

      if (item.imageKeys && item.imageKeys.length > 0) {
        post.imageUrls = item.imageKeys.map((key: string) => generateBlobReadUrl(key));
      }

      return post;
    });

    const responseBody: any = { items: posts, limit };

    // Set continuation token if there are more results
    if (newToken) {
      responseBody.continuationToken = newToken;
    }

    return {
      status: 200,
      jsonBody: responseBody,
      headers: {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Credentials': 'true'
      }
    };
  } catch (error) {
    context.error('Error listing posts:', error);
    return {
      status: 500,
      jsonBody: { message: 'Internal server error' }
    };
  }
}

app.http('listPosts', {
  methods: ['GET', 'OPTIONS'],
  authLevel: 'anonymous',
  route: 'listposts',
  handler: listPosts
});
