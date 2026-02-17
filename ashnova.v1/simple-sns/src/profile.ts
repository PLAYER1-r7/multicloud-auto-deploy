import type { APIGatewayProxyHandler } from "aws-lambda";
import { DynamoDBClient } from "@aws-sdk/client-dynamodb";
import { DynamoDBDocumentClient, GetCommand, PutCommand } from "@aws-sdk/lib-dynamodb";
import {
  json,
  requireEnv,
  MIN_NICKNAME_LENGTH,
  MAX_NICKNAME_LENGTH,
  buildUserProfileKey,
} from "./common";
import { handleError, extractUserInfo } from "./middleware/errorHandler";
import { AuthenticationError, ValidationError } from "./utils/errors";
import { logger } from "./utils/logger";

const ddb = DynamoDBDocumentClient.from(new DynamoDBClient({}));

interface ProfilePayload {
  nickname?: string;
}

export const handler: APIGatewayProxyHandler = async (event) => {
  try {
    const table = requireEnv("POSTS_TABLE_NAME");

    const userInfo = extractUserInfo(event.requestContext.authorizer?.claims);
    if (!userInfo) {
      throw new AuthenticationError();
    }

    const { userId } = userInfo;
    const profileKey = buildUserProfileKey(userId);

    if (event.httpMethod === "GET") {
      const res = await ddb.send(
        new GetCommand({
          TableName: table,
          Key: profileKey,
        })
      );

      if (!res.Item) {
        return json(200, { userId, nickname: "" });
      }

      return json(200, {
        userId,
        nickname: res.Item.nickname || "",
        updatedAt: res.Item.updatedAt,
        createdAt: res.Item.createdAt,
      });
    }

    if (event.httpMethod === "POST") {
      const body = event.body ? (JSON.parse(event.body) as ProfilePayload) : {};
      const rawNickname = typeof body.nickname === "string" ? body.nickname.trim() : "";

      if (rawNickname.length < MIN_NICKNAME_LENGTH) {
        throw new ValidationError("ニックネームを入力してください");
      }

      if (rawNickname.length > MAX_NICKNAME_LENGTH) {
        throw new ValidationError(`ニックネームは${MAX_NICKNAME_LENGTH}文字以内で入力してください`);
      }

      const now = new Date().toISOString();
      const existing = await ddb.send(
        new GetCommand({
          TableName: table,
          Key: profileKey,
        })
      );
      const createdAt = (existing.Item?.createdAt as string | undefined) || now;

      await ddb.send(
        new PutCommand({
          TableName: table,
          Item: {
            ...profileKey,
            userId,
            nickname: rawNickname,
            updatedAt: now,
            createdAt,
            docType: "profile",
          },
        })
      );

      logger.info("Profile updated", { userId });
      return json(200, {
        userId,
        nickname: rawNickname,
        updatedAt: now,
        createdAt,
      });
    }

    return json(405, { message: "Method not allowed" });
  } catch (err: unknown) {
    return handleError(err, "profile");
  }
};
