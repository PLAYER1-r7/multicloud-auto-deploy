import type { APIGatewayProxyHandler } from "aws-lambda";
import { DynamoDBClient } from "@aws-sdk/client-dynamodb";
import { DynamoDBDocumentClient, BatchGetCommand, QueryCommand } from "@aws-sdk/lib-dynamodb";
import { S3Client, GetObjectCommand } from "@aws-sdk/client-s3";
import { getSignedUrl } from "@aws-sdk/s3-request-presigner";
import { json, parseLimit, requireEnv, getEnvOrDefault, buildUserProfileKey } from "./common";
import type { Post, ListPostsResponse } from "./types";
import { handleError } from "./middleware/errorHandler";
import { InternalServerError } from "./utils/errors";
import { logger } from "./utils/logger";

const ddb = DynamoDBDocumentClient.from(new DynamoDBClient({}));
const s3 = new S3Client({});
const SIGNED_URL_EXPIRY = parseInt(getEnvOrDefault('SIGNED_URL_EXPIRY', '3600'), 10); // 1 hour default

export const handler: APIGatewayProxyHandler = async (event) => {
  try {
    const table = requireEnv("POSTS_TABLE_NAME");
    const bucketName = requireEnv("IMAGES_BUCKET_NAME");
    const limit = parseLimit(event.queryStringParameters?.limit, 50, 20);
    const inputNextToken = event.queryStringParameters?.nextToken;
    const tagFilter = event.queryStringParameters?.tag; // Tag filter parameter

    // Decode nextToken if provided
    let exclusiveStartKey: Record<string, any> | undefined;
    if (inputNextToken) {
      try {
        exclusiveStartKey = JSON.parse(Buffer.from(inputNextToken, 'base64').toString('utf-8'));
      } catch (err) {
        logger.warn('Invalid nextToken provided', { error: err });
      }
    }

    const res = await ddb.send(
      new QueryCommand({
        TableName: table,
        KeyConditionExpression: "PK = :pk",
        ExpressionAttributeValues: { ":pk": "POSTS" },
        ScanIndexForward: false, // 新しい順
        Limit: limit,
        ...(exclusiveStartKey && { ExclusiveStartKey: exclusiveStartKey })
      })
    );

    const userIds = Array.from(
      new Set((res.Items ?? [])
        .map((x) => x.userId as string | undefined)
        .filter((id): id is string => !!id))
    );

    const nicknameByUserId = new Map<string, string>();
    if (userIds.length > 0) {
      const profileKeys = userIds.map((userId) => buildUserProfileKey(userId));
      const profileRes = await ddb.send(
        new BatchGetCommand({
          RequestItems: {
            [table]: {
              Keys: profileKeys,
            },
          },
        })
      );

      const profiles = profileRes.Responses?.[table] ?? [];
      profiles.forEach((item) => {
        const nickname = typeof item.nickname === 'string' ? item.nickname.trim() : '';
        if (nickname) {
          nicknameByUserId.set(item.userId as string, nickname);
        }
      });
    }

    // Generate signed URLs for images and filter by tag if specified
    const items: Post[] = await Promise.all((res.Items ?? []).map(async (x) => {
      const post: Post = {
        postId: x.postId as string,
        userId: x.userId as string,
        ...(x.nickname && { nickname: x.nickname as string }),
        content: x.content as string,
        createdAt: x.createdAt as string,
        ...(x.isMarkdown && { isMarkdown: true }),
        ...(x.tags && { tags: x.tags as string[] })
      };

      const profileNickname = nicknameByUserId.get(post.userId);
      if (profileNickname) {
        post.nickname = profileNickname;
      }

      // Support both single image (backward compatibility) and multiple images
      const imageKeys = x.imageKeys as string[] | undefined;
      const singleImageKey = x.imageKey as string | undefined;
      
      if (imageKeys && imageKeys.length > 0) {
        // Multiple images: generate signed URLs for all
        try {
          post.imageUrls = await Promise.all(
            imageKeys.map(async (key) => {
              const command = new GetObjectCommand({
                Bucket: bucketName,
                Key: key
              });
              return await getSignedUrl(s3, command, { expiresIn: SIGNED_URL_EXPIRY });
            })
          );
        } catch (err) {
          logger.error('Failed to generate signed URLs for images', { 
            error: err, 
            imageKeys,
            postId: x.postId 
          });
          // Continue without image URLs
        }
      } else if (singleImageKey) {
        // Backward compatibility: single image
        try {
          const command = new GetObjectCommand({
            Bucket: bucketName,
            Key: singleImageKey
          });
          const url = await getSignedUrl(s3, command, { expiresIn: SIGNED_URL_EXPIRY });
          post.imageUrl = url;
          post.imageUrls = [url]; // Also populate imageUrls for consistency
        } catch (err) {
          logger.error('Failed to generate signed URL for image', { 
            error: err, 
            imageKey: singleImageKey,
            postId: x.postId 
          });
          // Continue without image URL
        }
      }

      return post;
    }));

    // Filter by tag if specified
    const filteredItems = tagFilter 
      ? items.filter(item => item.tags?.includes(tagFilter))
      : items;

    // Encode LastEvaluatedKey as nextToken
    let outputNextToken: string | undefined;
    if (res.LastEvaluatedKey) {
      outputNextToken = Buffer.from(JSON.stringify(res.LastEvaluatedKey)).toString('base64');
    }

    const response: ListPostsResponse = { items: filteredItems, limit, nextToken: outputNextToken };
    logger.info('Posts retrieved successfully', { count: filteredItems.length, hasMore: !!outputNextToken, tagFilter });
    return json(200, response);
  } catch (err: unknown) {
    return handleError(err, 'listPosts');
  }
};