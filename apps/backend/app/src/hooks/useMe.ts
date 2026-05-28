import { useFetch } from './useFetch';
import { api } from '@/api/client';

export function useMe() {
  return useFetch('me', () => api.me());
}
