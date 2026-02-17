import type { Request, Response } from '@google-cloud/functions-framework';
import {
  db,
  extractUserInfo,
  jsonResponse,
  handleCorsOptions,
  MIN_NICKNAME_LENGTH,
  MAX_NICKNAME_LENGTH,
  USER_PROFILE_COLLECTION,
} from '../common';

interface ProfilePayload {
  nickname?: string;
}

/**
 * Cloud Function: Profile
 * GET /api/profile
 * POST /api/profile
 */
export async function profile(req: Request, res: Response) {
  if (handleCorsOptions(req, res)) return;

  try {
    const userInfo = await extractUserInfo(req);
    if (!userInfo) {
      return jsonResponse(res, 401, { message: 'Unauthorized' });
    }

    const docRef = db.collection(USER_PROFILE_COLLECTION).doc(userInfo.userId);

    if (req.method === 'GET') {
      const doc = await docRef.get();
      if (!doc.exists) {
        return jsonResponse(res, 200, { userId: userInfo.userId, nickname: '' });
      }
      const data = doc.data() as ProfilePayload & { updatedAt?: string; createdAt?: string };
      return jsonResponse(res, 200, {
        userId: userInfo.userId,
        nickname: data?.nickname || '',
        updatedAt: data?.updatedAt,
        createdAt: data?.createdAt,
      });
    }

    if (req.method === 'POST') {
      const body = (req.body || {}) as ProfilePayload;
      const rawNickname = typeof body.nickname === 'string' ? body.nickname.trim() : '';

      if (rawNickname.length < MIN_NICKNAME_LENGTH) {
        return jsonResponse(res, 400, { message: 'Nickname is required' });
      }

      if (rawNickname.length > MAX_NICKNAME_LENGTH) {
        return jsonResponse(res, 400, {
          message: `Nickname must be ${MAX_NICKNAME_LENGTH} characters or less`,
        });
      }

      const now = new Date().toISOString();
      const existing = await docRef.get();
      const createdAt = existing.exists
        ? (existing.data() as { createdAt?: string })?.createdAt || now
        : now;

      await docRef.set(
        {
          userId: userInfo.userId,
          nickname: rawNickname,
          updatedAt: now,
          createdAt,
        },
        { merge: true }
      );

      return jsonResponse(res, 200, {
        userId: userInfo.userId,
        nickname: rawNickname,
        updatedAt: now,
        createdAt,
      });
    }

    return jsonResponse(res, 405, { message: 'Method not allowed' });
  } catch (error) {
    console.error('Error handling profile:', error);
    return jsonResponse(res, 500, { message: 'Internal server error' });
  }
}
