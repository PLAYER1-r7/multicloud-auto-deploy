import type { Request, Response } from '@google-cloud/functions-framework';
import { db, storage, extractUserInfo, jsonResponse, handleCorsOptions } from '../common';
import type { Post } from '../types';

/**
 * Cloud Function: Delete Post
 * DELETE /api/posts/:postId
 */
export async function deletePost(req: Request, res: Response) {
  if (handleCorsOptions(req, res)) return;

  try {
    // Authentication
    const userInfo = await extractUserInfo(req);
    if (!userInfo) {
      return jsonResponse(res, 401, { message: 'Unauthorized' });
    }

    // Get postId from path
    const postId = req.path.split('/').pop();
    if (!postId) {
      return jsonResponse(res, 400, { message: 'Post ID is required' });
    }

    // Get post from Firestore
    const postDoc = await db.collection('posts').doc(postId).get();

    if (!postDoc.exists) {
      return jsonResponse(res, 404, { message: 'Post not found' });
    }

    const post = postDoc.data() as Post;

    // Check ownership
    if (post.userId !== userInfo.userId) {
      return jsonResponse(res, 403, { message: 'Forbidden: You can only delete your own posts' });
    }

    // Delete images from Cloud Storage
    if (post.imageKeys && post.imageKeys.length > 0) {
      const bucket = storage.bucket(process.env.STORAGE_BUCKET || 'simple-sns-gcp-images');
      await Promise.all(
        post.imageKeys.map((key) => bucket.file(key).delete().catch(() => {}))
      );
    }

    // Delete post from Firestore
    await db.collection('posts').doc(postId).delete();

    console.log('Post deleted:', { postId, userId: userInfo.userId });
    return jsonResponse(res, 200, { message: 'Post deleted successfully' });
  } catch (error) {
    console.error('Error deleting post:', error);
    return jsonResponse(res, 500, { message: 'Internal server error' });
  }
}
