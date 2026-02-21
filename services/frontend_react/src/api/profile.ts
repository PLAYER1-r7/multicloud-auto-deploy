import apiClient from "./client";
import type { Profile } from "../types/message";

export const profileApi = {
  async getProfile(): Promise<Profile> {
    const res = await apiClient.get<Profile>("/profile");
    return res.data;
  },

  async updateProfile(data: { nickname: string }): Promise<Profile> {
    const res = await apiClient.put<Profile>("/profile", data);
    return res.data;
  },
};
