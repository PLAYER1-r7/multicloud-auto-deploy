import { app, HttpRequest, HttpResponseInit, InvocationContext } from '@azure/functions';
import { CosmosClient } from '@azure/cosmos';
import {
  requireEnv,
  jsonResponse,
  extractUserInfo,
  CORS_HEADERS,
  MIN_NICKNAME_LENGTH,
  MAX_NICKNAME_LENGTH,
  PROFILE_DOC_TYPE,
  buildProfileId,
} from '../common';

const cosmosClient = new CosmosClient({
  endpoint: requireEnv('COSMOS_DB_ENDPOINT'),
  key: requireEnv('COSMOS_DB_KEY'),
});

interface ProfilePayload {
  nickname?: string;
}

export async function profile(
  request: HttpRequest,
  context: InvocationContext
): Promise<HttpResponseInit> {
  try {
    if (request.method === 'OPTIONS') {
      return { status: 204, headers: CORS_HEADERS };
    }

    const userInfo = await extractUserInfo(request);
    if (!userInfo) {
      return jsonResponse(401, { message: 'Unauthorized' });
    }

    const database = cosmosClient.database(requireEnv('COSMOS_DB_DATABASE'));
    const container = database.container(requireEnv('COSMOS_DB_CONTAINER'));
    const profileId = buildProfileId(userInfo.userId);

    if (request.method === 'GET') {
      try {
        const res = await container.item(profileId, userInfo.userId).read();
        if (!res.resource) {
          return jsonResponse(200, { userId: userInfo.userId, nickname: '' });
        }
        return jsonResponse(200, {
          userId: userInfo.userId,
          nickname: res.resource.nickname || '',
          updatedAt: res.resource.updatedAt,
          createdAt: res.resource.createdAt,
        });
      } catch {
        return jsonResponse(200, { userId: userInfo.userId, nickname: '' });
      }
    }

    if (request.method === 'POST') {
      const body = (await request.json()) as ProfilePayload;
      const rawNickname = typeof body.nickname === 'string' ? body.nickname.trim() : '';

      if (rawNickname.length < MIN_NICKNAME_LENGTH) {
        return jsonResponse(400, { message: 'Nickname is required' });
      }

      if (rawNickname.length > MAX_NICKNAME_LENGTH) {
        return jsonResponse(400, {
          message: `Nickname must be ${MAX_NICKNAME_LENGTH} characters or less`,
        });
      }

      const now = new Date().toISOString();
      let createdAt = now;
      try {
        const existing = await container.item(profileId, userInfo.userId).read();
        if (existing.resource?.createdAt) {
          createdAt = existing.resource.createdAt;
        }
      } catch {
        createdAt = now;
      }

      await container.items.upsert({
        id: profileId,
        userId: userInfo.userId,
        nickname: rawNickname,
        updatedAt: now,
        createdAt,
        docType: PROFILE_DOC_TYPE,
      });

      return jsonResponse(200, {
        userId: userInfo.userId,
        nickname: rawNickname,
        updatedAt: now,
        createdAt,
      });
    }

    return jsonResponse(405, { message: 'Method not allowed' });
  } catch (error) {
    context.error('Error handling profile:', error);
    return jsonResponse(500, { message: 'Internal server error' });
  }
}

app.http('profile', {
  methods: ['GET', 'POST', 'OPTIONS'],
  authLevel: 'anonymous',
  route: 'profile',
  handler: profile,
});
