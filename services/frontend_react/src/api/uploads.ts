import apiClient from './client';
import type { PresignedUrlsResponse } from '../types/message';

export const uploadsApi = {
  /** Request presigned PUT URLs from the API */
  async getPresignedUrls(
    count: number,
    contentTypes: string[],
  ): Promise<PresignedUrlsResponse> {
    const res = await apiClient.post<PresignedUrlsResponse>(
      '/uploads/presigned-urls',
      { count, contentTypes },
    );
    return res.data;
  },

  /** Upload a single file directly to the presigned URL */
  async uploadFile(
    presignedUrl: string,
    file: File,
  ): Promise<void> {
    await fetch(presignedUrl, {
      method: 'PUT',
      body: file,
      headers: { 'Content-Type': file.type },
    }).then((res) => {
      if (!res.ok) throw new Error(`Upload failed: ${res.status}`);
    });
  },
};
