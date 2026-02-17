import type { APIGatewayProxyHandler } from "aws-lambda";
import { DynamoDBClient } from "@aws-sdk/client-dynamodb";
import { DynamoDBDocumentClient, GetCommand, PutCommand } from "@aws-sdk/lib-dynamodb";
import { json, requireEnv, MAX_IMAGES_PER_POST, buildUserProfileKey } from "./common";
import type { PostItem } from "./types";
import { validateCreatePostBody } from "./utils/validation";
import { handleError, extractUserInfo } from "./middleware/errorHandler";
import { AuthenticationError, ValidationError } from "./utils/errors";
import { logger } from "./utils/logger";
import crypto from "crypto";

const ddb = DynamoDBDocumentClient.from(new DynamoDBClient({}));

export const handler: APIGatewayProxyHandler = async (event) => {
  try {
    const table = requireEnv("POSTS_TABLE_NAME");
    
    // Authentication check
    const userInfo = extractUserInfo(event.requestContext.authorizer?.claims);
    if (!userInfo) {
      throw new AuthenticationError();
    }
    
    const { userId } = userInfo;
    
    // Parse and validate request body
    const body = event.body ? JSON.parse(event.body) : {};
    const validationResult = validateCreatePostBody(body);
    
    if (!validationResult.success) {
      throw new ValidationError(validationResult.error);
    }
    
    const { content, imageKeys, isMarkdown, tags } = validationResult.data;
    const postId = crypto.randomUUID();
    const createdAt = new Date().toISOString();
    
    // Validate imageKeys if provided
    if (imageKeys && imageKeys.length > MAX_IMAGES_PER_POST) {
      throw new ValidationError(`Maximum ${MAX_IMAGES_PER_POST} images allowed per post`);
    }
    
    // Get user nickname from claims
    const profileKey = buildUserProfileKey(userId);
    const profileRes = await ddb.send(
      new GetCommand({
        TableName: table,
        Key: profileKey,
      })
    );
    const profileNickname = typeof profileRes.Item?.nickname === 'string'
      ? profileRes.Item.nickname
      : undefined;
    const nickname = profileNickname || event.requestContext.authorizer?.claims?.nickname;
    
    // Create post item
    const item: PostItem = {
      PK: "POSTS",
      SK: `${createdAt}#${postId}`,
      postId,
      userId,
      ...(nickname && { nickname }),
      content,
      createdAt,
      ...(imageKeys && imageKeys.length > 0 && { imageKeys }),
      ...(isMarkdown && { isMarkdown: true }),
      ...(tags && tags.length > 0 && { tags })
    };

    await ddb.send(new PutCommand({ TableName: table, Item: item }));
    
    logger.info('Post created successfully', { postId, userId, imageCount: imageKeys?.length || 0 });
    return json(201, { item });
  } catch (err: unknown) {
    return handleError(err, 'createPost');
  }
};