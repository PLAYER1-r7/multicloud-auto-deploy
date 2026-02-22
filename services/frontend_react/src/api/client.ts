import axios from 'axios';

// VITE_API_URL: backend API base (https://api.example.com)
// Empty string in dev → Vite proxy forwards to localhost:8000
const API_URL = import.meta.env.VITE_API_URL ?? '';

const apiClient = axios.create({
  baseURL: API_URL,
  headers: { 'Content-Type': 'application/json' },
  timeout: 15000,
});

// Attach stored auth token to every request
// id_token is preferred because the Lambda JWT verifier validates audience against the Cognito client_id,
// which matches the id_token aud claim. Cognito access tokens may omit the aud claim.
apiClient.interceptors.request.use((config) => {
  const token =
    localStorage.getItem('id_token') ||
    localStorage.getItem('access_token');
  if (token) {
    config.headers['Authorization'] = `Bearer ${token}`;
  }
  return config;
});

export default apiClient;
