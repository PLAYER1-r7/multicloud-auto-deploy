import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import { apiFetch, getToken } from '../services/api';
import type { UserProfile } from '../types';

const fetchProfile = async (): Promise<UserProfile> => {
  const { res, json } = await apiFetch('/profile', { method: 'GET' });

  if (!res.ok) {
    throw new Error(json?.message || `Failed to fetch profile: ${res.status}`);
  }

  return json as UserProfile;
};

const updateProfile = async (nickname: string): Promise<UserProfile> => {
  const { res, json } = await apiFetch('/profile', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ nickname }),
  });

  if (!res.ok) {
    throw new Error(json?.message || `Failed to update profile: ${res.status}`);
  }

  return json as UserProfile;
};

export const useProfile = (enabled: boolean) => {
  return useQuery({
    queryKey: ['profile'],
    queryFn: fetchProfile,
    enabled: enabled && !!getToken(),
    staleTime: 30000,
  });
};

export const useUpdateProfile = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: updateProfile,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['profile'] });
      queryClient.invalidateQueries({ queryKey: ['posts'] });
      toast.success('ニックネームを更新しました');
    },
    onError: (error: Error) => {
      toast.error(error.message || 'ニックネームの更新に失敗しました');
    },
  });
};
