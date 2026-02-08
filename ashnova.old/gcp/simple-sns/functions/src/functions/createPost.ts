import type { Request, Response } from '@google-cloud/functions-framework';
import { db, extractUserInfo, jsonResponse, handleCorsOptions, MAX_CONTENT_LENGTH, MAX_IMAGES_PER_POST, MAX_TAGS_PER_POST, getNicknameByUserId } from '../common';
import type { Post } from '../types';
import { nanoid } from 'nanoid';

/**
 * Cloud Function: Create Post
 * POST /api/posts
 */
export async function createPost(req: Request, res: Response) {
  if (handleCorsOptions(req, res)) return;

  try {
    // Authentication
    const userInfo = await extractUserInfo(req);
    if (!userInfo) {
      return jsonResponse(res, 401, { message: 'Unauthorized' });
    }

    // Validation
    const { content, imageKeys, isMarkdown, tags } = req.body;

    if (!content || typeof content !== 'string') {
      return jsonResponse(res, 400, { message: 'Content is required' });
    }

    if (content.length > MAX_CONTENT_LENGTH) {
      return jsonResponse(res, 400, { message: `Content must be less than ${MAX_CONTENT_LENGTH} characters` });
    }

    if (imageKeys && (!Array.isArray(imageKeys) || imageKeys.length > MAX_IMAGES_PER_POST)) {
      return jsonResponse(res, 400, { message: `Maximum ${MAX_IMAGES_PER_POST} images allowed` });
    }

    if (tags && (!Array.isArray(tags) || tags.length > MAX_TAGS_PER_POST)) {
      return jsonResponse(res, 400, { message: `Maximum ${MAX_TAGS_PER_POST} tags allowed` });
    }

    // Create post
    const postId = nanoid();
    const createdAt = new Date().toISOString();

    const profileNickname = await getNicknameByUserId(userInfo.userId);
    const nickname = profileNickname || userInfo.nickname;

    const post: Post = {
      postId,
      userId: userInfo.userId,
      ...(nickname && { nickname }),
      content,
      createdAt,
      ...(imageKeys && imageKeys.length > 0 && { imageKeys }),
      ...(isMarkdown && { isMarkdown: true }),
      ...(tags && tags.length > 0 && { tags }),
    };

    // Save to Firestore
    await db.collection('posts').doc(postId).set(post);

    console.log('Post created:', { postId, userId: userInfo.userId });
    return jsonResponse(res, 201, { item: post });
  } catch (error) {
    console.error('Error creating post:', error);
    return jsonResponse(res, 500, { message: 'Internal server error' });
  }
}
