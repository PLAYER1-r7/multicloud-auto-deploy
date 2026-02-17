import { app, HttpRequest, HttpResponseInit, InvocationContext } from '@azure/functions';
import { CosmosClient } from '@azure/cosmos';
import { requireEnv, jsonResponse, extractUserInfo, CORS_HEADERS } from '../common';

const cosmosClient = new CosmosClient({
  endpoint: requireEnv('COSMOS_DB_ENDPOINT'),
  key: requireEnv('COSMOS_DB_KEY'),
});

export async function deletePost(
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

    const postId = request.params.postId;
    if (!postId) {
      return jsonResponse(400, { message: 'Post ID is required' });
    }

    const database = cosmosClient.database(requireEnv('COSMOS_DB_DATABASE'));
    const container = database.container(requireEnv('COSMOS_DB_CONTAINER'));

    // Get the post to verify ownership
    try {
      const { resource: post } = await container.item(postId, postId).read();
      
      if (!post) {
        return jsonResponse(404, { message: 'Post not found' });
      }

      // Check if user owns the post
      if (post.userId !== userInfo.userId) {
        return jsonResponse(403, { message: 'Forbidden: You can only delete your own posts' });
      }

      // Delete the post
      await container.item(postId, postId).delete();

      context.log('Post deleted:', postId);

      return jsonResponse(200, { message: 'Post deleted successfully' });
    } catch (error: any) {
      if (error.code === 404) {
        return jsonResponse(404, { message: 'Post not found' });
      }
      throw error;
    }
  } catch (error) {
    context.error('Error deleting post:', error);
    return jsonResponse(500, { message: 'Internal server error' });
  }
}

app.http('deletePost', {
  methods: ['DELETE', 'OPTIONS'],
  authLevel: 'anonymous',
  route: 'posts/{postId}',
  handler: deletePost,
});
