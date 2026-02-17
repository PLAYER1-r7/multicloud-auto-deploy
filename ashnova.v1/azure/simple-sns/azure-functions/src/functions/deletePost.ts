import { app, HttpRequest, HttpResponseInit, InvocationContext } from '@azure/functions';
import { getCosmosContainer, getBlobServiceClient, extractUserInfo } from '../common';
import type { Post } from '../types';

/**
 * Azure Function: Delete Post
 * DELETE /api/posts/{postId}
 */
async function deletePost(request: HttpRequest, context: InvocationContext): Promise<HttpResponseInit> {
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

    // Get postId from route parameter
    const postId = request.params.postId;
    if (!postId) {
      return {
        status: 400,
        jsonBody: { message: 'Post ID is required' }
      };
    }

    // Get post from Cosmos DB
    const container = getCosmosContainer();
    try {
      const { resource: post } = await container.item(postId, postId).read<Post>();

      if (!post) {
        return {
          status: 404,
          jsonBody: { message: 'Post not found' }
        };
      }

      // Check ownership
      if (post.userId !== userInfo.userId) {
        return {
          status: 403,
          jsonBody: { message: 'Forbidden: You can only delete your own posts' }
        };
      }

      // Delete images from Blob Storage
      if (post.imageKeys && post.imageKeys.length > 0) {
        const blobServiceClient = getBlobServiceClient();
        const containerClient = blobServiceClient.getContainerClient('post-images');
        
        await Promise.all(
          post.imageKeys.map(async (key) => {
            try {
              const blobClient = containerClient.getBlobClient(key);
              await blobClient.delete();
            } catch (err) {
              context.warn(`Failed to delete blob ${key}:`, err);
            }
          })
        );
      }

      // Delete post from Cosmos DB
      await container.item(postId, postId).delete();

      context.log('Post deleted:', { postId, userId: userInfo.userId });
      
      return {
        status: 200,
        jsonBody: { message: 'Post deleted successfully' },
        headers: {
          'Access-Control-Allow-Origin': '*',
          'Access-Control-Allow-Credentials': 'true'
        }
      };
    } catch (error: any) {
      if (error.code === 404) {
        return {
          status: 404,
          jsonBody: { message: 'Post not found' }
        };
      }
      throw error;
    }
  } catch (error) {
    context.error('Error deleting post:', error);
    return {
      status: 500,
      jsonBody: { message: 'Internal server error' }
    };
  }
}

app.http('deletePost', {
  methods: ['DELETE', 'OPTIONS'],
  authLevel: 'anonymous',
  route: 'posts/{postId}',
  handler: deletePost
});
