import type { Request, Response } from '@google-cloud/functions-framework';
import { db, storage, jsonResponse, handleCorsOptions, SAS_URL_EXPIRY_MINUTES, USER_PROFILE_COLLECTION } from '../common';
import type { Post } from '../types';

/**
 * Cloud Function: List Posts
 * GET /api/posts?limit=20&continuationToken=...&tag=...
 */
export async function listPosts(req: Request, res: Response) {
  if (handleCorsOptions(req, res)) return;

  try {
    const limit = Math.min(parseInt(req.query.limit as string) || 20, 100);
    const tag = req.query.tag as string;
    const continuationToken = req.query.continuationToken as string;

    // Query Firestore
    let query = db.collection('posts').orderBy('createdAt', 'desc').limit(limit);

    // Filter by tag if provided
    if (tag) {
      query = query.where('tags', 'array-contains', tag) as any;
    }

    // Start after continuation token if provided
    if (continuationToken) {
      const lastDoc = await db.collection('posts').doc(continuationToken).get();
      if (lastDoc.exists) {
        query = query.startAfter(lastDoc) as any;
      }
    }

    const snapshot = await query.get();
    const posts: Post[] = [];

    const userIds = new Set<string>();
    snapshot.docs.forEach((doc) => {
      const data = doc.data() as Post;
      if (data.userId) {
        userIds.add(data.userId);
      }
    });

    const nicknameByUserId = new Map<string, string>();
    if (userIds.size > 0) {
      const profileRefs = Array.from(userIds).map((userId) =>
        db.collection(USER_PROFILE_COLLECTION).doc(userId)
      );
      const profileDocs = await db.getAll(...profileRefs);
      profileDocs.forEach((doc) => {
        if (!doc.exists) return;
        const data = doc.data() as { nickname?: string } | undefined;
        const nickname = data?.nickname?.trim();
        if (nickname) {
          nicknameByUserId.set(doc.id, nickname);
        }
      });
    }

    // Generate signed URLs for images
    const bucket = storage.bucket(process.env.STORAGE_BUCKET || 'simple-sns-gcp-images');

    for (const doc of snapshot.docs) {
      const data = doc.data() as Post;
      const post: Post = { ...data };
      const profileNickname = nicknameByUserId.get(data.userId);
      if (profileNickname) {
        post.nickname = profileNickname;
      }

      if (data.imageKeys && data.imageKeys.length > 0) {
        post.imageUrls = await Promise.all(
          data.imageKeys.map(async (key) => {
            const file = bucket.file(key);
            const [url] = await file.getSignedUrl({
              version: 'v4',
              action: 'read',
              expires: Date.now() + SAS_URL_EXPIRY_MINUTES * 60 * 1000,
            });
            return url;
          })
        );
      }

      posts.push(post);
    }

    const response: any = { items: posts, limit };

    // Set continuation token if there are more results
    if (snapshot.docs.length === limit) {
      const lastDoc = snapshot.docs[snapshot.docs.length - 1];
      response.continuationToken = lastDoc.id;
    }

    return jsonResponse(res, 200, response);
  } catch (error) {
    console.error('Error listing posts:', error);
    return jsonResponse(res, 500, { message: 'Internal server error' });
  }
}
