import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { TextInput, PasswordInput } from '@mantine/core';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { IconLoader2 } from '@tabler/icons-react';
import { authService } from '../../../mocks/services/auth.service';
import { useAuth } from '../../../store/AuthContext';

const schema = z.object({
  email: z.string().min(1, 'Email is required').email('Enter a valid email address'),
  password: z.string().min(3, 'Password must be at least 3 characters'),
});

type FormValues = z.infer<typeof schema>;

const DEMO_CREDENTIALS = [
  { email: 'client@acme.com',  role: 'Client' },
  { email: 'onboard@bank.com', role: 'Onboarding Team' },
  { email: 'sales@bank.com',   role: 'Sales' },
  { email: 'risk@bank.com',    role: 'Risk & Compliance' },
];

export default function SignInPage() {
  const navigate = useNavigate();
  const auth = useAuth();
  const [serverError, setServerError] = useState('');

  const {
    register,
    handleSubmit,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  const onSubmit = async (data: FormValues) => {
    setServerError('');
    try {
      const user = await authService.signIn(data.email, data.password);
      auth.signIn(user);
      if (user.role === 'client') {
        navigate('/client/dashboard');
      } else {
        navigate('/internal/dashboard');
      }
    } catch (err) {
      setServerError(err instanceof Error ? err.message : 'Sign in failed. Please try again.');
    }
  };

  return (
    <div className="bg-bg-surface border border-border-default rounded-xl p-8 shadow-xl w-full">
      <h2 className="text-2xl font-bold text-text-primary mb-1">Welcome back</h2>
      <p className="text-sm text-text-secondary mb-6">Sign in to your ClearPath account</p>

      <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-4">
        <div>
          <TextInput
            label="Email address"
            placeholder="you@example.com"
            autoComplete="email"
            data-autofocus
            classNames={{
              label: 'text-text-secondary text-sm mb-1',
              error: 'text-danger text-xs mt-1',
            }}
            error={errors.email?.message}
            {...register('email')}
          />
        </div>

        <div>
          <PasswordInput
            label="Password"
            placeholder="••••••••"
            autoComplete="current-password"
            classNames={{
              label: 'text-text-secondary text-sm mb-1',
              error: 'text-danger text-xs mt-1',
            }}
            error={errors.password?.message}
            {...register('password')}
          />
        </div>

        {serverError && (
          <div className="px-3 py-2 rounded-lg bg-danger/10 border border-danger/20 text-danger text-sm">
            {serverError}
          </div>
        )}

        <button
          type="submit"
          disabled={isSubmitting}
          className="w-full flex items-center justify-center gap-2 h-10 rounded-lg bg-primary hover:bg-primary-hover disabled:opacity-60 disabled:cursor-not-allowed text-white text-sm font-semibold transition-colors mt-2"
        >
          {isSubmitting && <IconLoader2 size={16} className="animate-spin" />}
          {isSubmitting ? 'Signing in…' : 'Sign in'}
        </button>
      </form>

      <p className="mt-5 text-sm text-center text-text-secondary">
        Don&apos;t have an account?{' '}
        <Link to="/auth/signup" className="text-primary hover:underline font-medium">
          Sign up
        </Link>
      </p>

      {/* Demo credentials */}
      <div className="mt-6 pt-5 border-t border-border-default">
        <p className="text-xs text-text-muted mb-2 font-medium uppercase tracking-wider">
          Demo credentials (any password)
        </p>
        <div className="space-y-1">
          {DEMO_CREDENTIALS.map(({ email, role }) => (
            <button
              key={email}
              type="button"
              onClick={() => setValue('email', email)}
              className="w-full flex items-center justify-between px-3 py-1.5 rounded-lg hover:bg-bg-elevated transition-colors group text-left"
            >
              <span className="text-xs text-text-secondary font-mono group-hover:text-text-primary transition-colors">
                {email}
              </span>
              <span className="text-xs text-text-muted group-hover:text-text-secondary transition-colors">
                {role}
              </span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
