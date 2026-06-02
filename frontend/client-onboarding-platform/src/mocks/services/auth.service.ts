import type { User } from '../../types';
import { MOCK_USERS } from '../data/users.mock';

const delay = (ms = 500) => new Promise(r => setTimeout(r, ms));

export const authService = {
  async signIn(email: string, _password: string): Promise<User> {
    await delay();
    const user = MOCK_USERS.find(u => u.email === email);
    if (!user) throw new Error('Invalid email or password.');
    return user;
  },

  async signUp(email: string, fullName: string, _password: string): Promise<User> {
    await delay();
    const existing = MOCK_USERS.find(u => u.email === email);
    if (existing) throw new Error('An account with this email already exists.');
    const newUser: User = {
      id: `u-${Date.now()}`,
      email,
      fullName,
      role: 'client',
      createdAt: new Date().toISOString(),
    };
    MOCK_USERS.push(newUser);
    return newUser;
  },
};
