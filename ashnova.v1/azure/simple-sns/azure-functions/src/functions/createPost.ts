import { app, HttpRequest, HttpResponseInit, InvocationContext } from '@azure/functions';
import { getCosmosContainer, extractUserInfo, MAX_CONTENT_LENGTH, MAX_IMAGES_PER_POST, MAX_TAGS_PER_POST } from '../common';
import type { Post } from '../types';
import { nanoid } from 'nanoid';

/**
 * Azure Function: Create Post
 * POST /api/posts
 */
async function createPost(request: HttpRequest, context: InvocationContext): Promise<HttpResponseInit> {
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
    const body = await request.json() as any;
    const { content, imageKeys, isMarkdown, tags } = body;

    // Validation
    if (!content || typeof content !== 'string') {
      return {
        status: 400,
        jsonBody: { message: 'Content is required' }
      };
    }

    if (content.length > MAX_CONTENT_LENGTH) {
      return {
        status: 400,
        jsonBody: { message: `Content must be ${MAX_CONTENT_LENGTH} characters or less` }
      };
    }

    if (imageKeys && (!Array.isArray(imageKeys) || imageKeys.length > MAX_IMAGES_PER_POST)) {
      return {
        status: 400,
        jsonBody: { message: `Maximum ${MAX_IMAGES_PER_POST} images per post` }
      };
    }

    if (tags && (!Array.isArray(tags) || tags.length > MAX_TAGS_PER_POST)) {
      return {
        status: 400,
        jsonBody: { message: `Maximum ${MAX_TAGS_PER_POST} tags per post` }
      };
    }

    // Create post
    const postId = nanoid();
    const post: Post = {
      postId,
      userId: userInfo.userId,
      content,
      createdAt: new Date().toISOString(),
      ...(imageKeys && imageKeys.length > 0 && { imageKeys }),
      ...(isMarkdown && { isMarkdown }),
      ...(tags && tags.length > 0 && { tags }),
    };

    // Save to Cosmos DB
    const container = getCosmosContainer();
    await container.items.create({
      id: postId,
      ...post,
    });

    context.log('Post created:', { postId, userId: userInfo.userId });
    
    return {
      status: 201,
      jsonBody: post,
      headers: {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Credentials': 'true'
      }
    };
  } catch (error) {
    context.error('Error creating post:', error);
    return {
      status: 500,
      jsonBody: { message: 'Internal server error' }
    };
  }
}

app.http('createPost', {
  methods: ['POST', 'OPTIONS'],
  authLevel: 'anonymous',
  route: 'createPost',
  handler: createPost
});
