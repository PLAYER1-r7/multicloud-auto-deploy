import { CosmosClient, Container } from '@azure/cosmos';
import { BlobServiceClient, StorageSharedKeyCredential, generateBlobSASQueryParameters, BlobSASPermissions } from '@azure/storage-blob';
import jwt from 'jsonwebtoken';
import jwksClient from 'jwks-rsa';

// JWKS client for Azure AD token validation
const client = jwksClient({
  jwksUri: `https://login.microsoftonline.com/${process.env.AZURE_AD_TENANT_ID || 'a3182bec-d835-4ce3-af06-04579abf597e'}/discovery/v2.0/keys`,
  cache: true,
  cacheMaxAge: 86400000, // 24 hours
});

// Get signing key from JWKS
function getKey(header: any, callback: any) {
  client.getSigningKey(header.kid, (err, key) => {
    if (err) {
      callback(err);
      return;
    }
    const signingKey = key?.getPublicKey();
    callback(null, signingKey);
  });
}

// Constants
export const MAX_IMAGES_PER_POST = 5;
export const MAX_TAGS_PER_POST = 10;
export const MAX_CONTENT_LENGTH = 5000;
export const SAS_URL_EXPIRY_MINUTES = 5;

export interface UserInfo {
  userId: string;
  email?: string;
}

// Cosmos DB client (lazy initialization)
let cosmosContainer: Container | null = null;

export function getCosmosContainer(): Container {
  if (!cosmosContainer) {
    const endpoint = process.env.COSMOS_ENDPOINT;
    const key = process.env.COSMOS_KEY;
    
    if (!endpoint || !key) {
      throw new Error('Cosmos DB configuration missing');
    }

    const client = new CosmosClient({ endpoint, key });
    const database = client.database('simple-sns-db');
    cosmosContainer = database.container('posts');
  }
  
  return cosmosContainer;
}

// Blob Storage client (lazy initialization)
let blobServiceClient: BlobServiceClient | null = null;

export function getBlobServiceClient(): BlobServiceClient {
  if (!blobServiceClient) {
    const accountName = process.env.STORAGE_ACCOUNT_NAME;
    const accountKey = process.env.STORAGE_ACCOUNT_KEY;
    
    if (!accountName || !accountKey) {
      throw new Error('Storage account configuration missing');
    }

    const sharedKeyCredential = new StorageSharedKeyCredential(accountName, accountKey);
    blobServiceClient = new BlobServiceClient(
      `https://${accountName}.blob.core.windows.net`,
      sharedKeyCredential
    );
  }
  
  return blobServiceClient;
}

/**
 * Extract user info from Azure AD token
 */
export async function extractUserInfo(authHeader?: string): Promise<UserInfo | null> {
  if (!authHeader || !authHeader.startsWith('Bearer ')) {
    return null;
  }

  const token = authHeader.substring(7);
  
  return new Promise((resolve) => {
    jwt.verify(token, getKey, {
      audience: process.env.AZURE_AD_CLIENT_ID || '00433640-13d1-4482-aa1b-db5f039197bf',
      issuer: `https://login.microsoftonline.com/${process.env.AZURE_AD_TENANT_ID || 'a3182bec-d835-4ce3-af06-04579abf597e'}/v2.0`,
      algorithms: ['RS256']
    }, (err, decoded: any) => {
      if (err) {
        console.error('Token verification failed:', err.message);
        resolve(null);
        return;
      }
      
      // Extract user info from token claims
      resolve({
        userId: decoded.oid || decoded.sub, // Azure AD object ID or subject
        email: decoded.email || decoded.preferred_username,
      });
    });
  });
}

/**
 * Generate SAS token for blob read
 */
export function generateBlobReadUrl(blobName: string): string {
  const accountName = process.env.STORAGE_ACCOUNT_NAME;
  const accountKey = process.env.STORAGE_ACCOUNT_KEY;
  
  if (!accountName || !accountKey) {
    throw new Error('Storage account configuration missing');
  }

  const sharedKeyCredential = new StorageSharedKeyCredential(accountName, accountKey);
  
  const sasToken = generateBlobSASQueryParameters({
    containerName: 'post-images',
    blobName: blobName,
    permissions: BlobSASPermissions.parse('r'),
    startsOn: new Date(),
    expiresOn: new Date(Date.now() + SAS_URL_EXPIRY_MINUTES * 60 * 1000),
  }, sharedKeyCredential).toString();

  return `https://${accountName}.blob.core.windows.net/post-images/${blobName}?${sasToken}`;
}

/**
 * Generate SAS token for blob write
 */
export function generateBlobWriteUrl(blobName: string): string {
  const accountName = process.env.STORAGE_ACCOUNT_NAME;
  const accountKey = process.env.STORAGE_ACCOUNT_KEY;
  
  if (!accountName || !accountKey) {
    throw new Error('Storage account configuration missing');
  }

  const sharedKeyCredential = new StorageSharedKeyCredential(accountName, accountKey);
  
  const sasToken = generateBlobSASQueryParameters({
    containerName: 'post-images',
    blobName: blobName,
    permissions: BlobSASPermissions.parse('w'),
    startsOn: new Date(),
    expiresOn: new Date(Date.now() + SAS_URL_EXPIRY_MINUTES * 60 * 1000),
  }, sharedKeyCredential).toString();

  return `https://${accountName}.blob.core.windows.net/post-images/${blobName}?${sasToken}`;
}
