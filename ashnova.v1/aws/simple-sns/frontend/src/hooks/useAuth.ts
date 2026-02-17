import { useState, useEffect } from 'react';
import { getToken } from '../services/api';

export const useAuth = () => {
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  useEffect(() => {
    setIsAuthenticated(!!getToken());
  }, []);

  const updateAuth = () => {
    setIsAuthenticated(!!getToken());
  };

  return { isAuthenticated, updateAuth };
};
