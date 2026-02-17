import { app, HttpRequest, HttpResponseInit, InvocationContext } from '@azure/functions';
import { CosmosClient } from '@azure/cosmos';
import { requireEnv, jsonResponse, extractUserInfo, MAX_CONTENT_LENGTH, MAX_IMAGES_PER_POST, MAX_TAGS_PER_POST, CORS_HEADERS, buildProfileId } from '../common';
import type { PostDocument, CreatePostBody } from '../types';
let nanoid: (() => string) | null = null;

const getNanoid = async (): Promise<() => string> => {
  if (!nanoid) {
    const { customAlphabet } = await import('nanoid');
    nanoid = customAlphabet('0123456789abcdefghijklmnopqrstuvwxyz', 21);
  }
  return nanoid;
};

const cosmosClient = new CosmosClient({
  endpoint: requireEnv('COSMOS_DB_ENDPOINT'),
  key: requireEnv('COSMOS_DB_KEY'),
});

export async function createPost(
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

    // Parse body
    const body: CreatePostBody = await request.json() as CreatePostBody;
    
    // Validation
    const trimmedContent = body.content?.trim() ?? '';
    const hasImages = Array.isArray(body.imageKeys) && body.imageKeys.length > 0;
    if (!trimmedContent && !hasImages) {
      return jsonResponse(400, { message: 'Content is required' });
    }
    
    if (trimmedContent.length > MAX_CONTENT_LENGTH) {
      return jsonResponse(400, { message: `Content must be less than ${MAX_CONTENT_LENGTH} characters` });
    }
    
    if (body.imageKeys && body.imageKeys.length > MAX_IMAGES_PER_POST) {
      return jsonResponse(400, { message: `Maximum ${MAX_IMAGES_PER_POST} images allowed` });
    }
    
    if (body.tags && body.tags.length > MAX_TAGS_PER_POST) {
      return jsonResponse(400, { message: `Maximum ${MAX_TAGS_PER_POST} tags allowed` });
    }

    const database = cosmosClient.database(requireEnv('COSMOS_DB_DATABASE'));
    const container = database.container(requireEnv('COSMOS_DB_CONTAINER'));

    const profileId = buildProfileId(userInfo.userId);
    let profileNickname: string | undefined;
    try {
      const profileRes = await container.item(profileId, userInfo.userId).read();
      const nickname = (profileRes.resource as { nickname?: string } | undefined)?.nickname;
      if (nickname && nickname.trim()) {
        profileNickname = nickname.trim();
      }
    } catch {
      profileNickname = undefined;
    }

    // Create post document
    const nanoidFn = await getNanoid();
    const postId = nanoidFn();
    const createdAt = new Date().toISOString();
    
    const document: PostDocument = {
      id: postId,
      docType: 'post',
      postId,
      userId: userInfo.userId,
      ...((profileNickname || userInfo.nickname) && { nickname: profileNickname || userInfo.nickname }),
      content: trimmedContent,
      createdAt,
      ...(body.imageKeys && body.imageKeys.length > 0 && { imageKeys: body.imageKeys }),
      ...(body.tags && body.tags.length > 0 && { tags: body.tags }),
    };

    // Save to Cosmos DB
    await container.items.create(document);

    context.log('Post created:', postId);

    return jsonResponse(201, { item: document });
  } catch (error) {
    context.error('Error creating post:', error);
    return jsonResponse(500, { message: 'Internal server error' });
  }
}

app.http('createPost', {
  methods: ['POST', 'OPTIONS'],
  authLevel: 'anonymous',
  route: 'posts',
  handler: createPost,
});
