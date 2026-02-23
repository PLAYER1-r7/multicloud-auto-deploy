import apiClient from "./client";
import type { PresignedUrlsResponse } from "../types/message";

export const uploadsApi = {
  /** Request presigned PUT URLs from the API */
  async getPresignedUrls(
    count: number,
    contentTypes: string[],
  ): Promise<PresignedUrlsResponse> {
    const res = await apiClient.post<PresignedUrlsResponse>(
      "/uploads/presigned-urls",
      { count, contentTypes },
    );
    return res.data;
  },

  /** Upload a single file directly to the presigned URL */
  async uploadFile(presignedUrl: string, file: File): Promise<void> {
    // Azure Blob Storage SAS PUT requires the x-ms-blob-type header.
    // Without it the request fails with 400 "mandatory header not specified".
    const isAzureBlob = presignedUrl.includes(".blob.core.windows.net");
    const headers: Record<string, string> = { "Content-Type": file.type };
    if (isAzureBlob) headers["x-ms-blob-type"] = "BlockBlob";

    await fetch(presignedUrl, {
      method: "PUT",
      body: file,
      headers,
    }).then((res) => {
      if (!res.ok) throw new Error(`Upload failed: ${res.status}`);
    });
  },
};
