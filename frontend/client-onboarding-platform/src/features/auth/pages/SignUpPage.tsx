import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { TextInput, PasswordInput } from '@mantine/core';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { IconLoader2 } from '@tabler/icons-react';
import { authService } from '../../../mocks/services/auth.service';
import { useAuth } from '../../../store/AuthContext';

const schema = z
  .object({
    fullName: z.string().min(1, 'Full name is required'),
    email: z.string().min(1, 'Email is required').email('Enter a valid email address'),
    password: z.string().min(8, 'Password must be at least 8 characters'),
    confirmPassword: z.string().min(1, 'Please confirm your password'),
  })
  .refine(data => data.password === data.confirmPassword, {
    message: 'Passwords do not match',
    path: ['confirmPassword'],
  });

type FormValues = z.infer<typeof schema>;

export default function SignUpPage() {
  const navigate = useNavigate();
  const auth = useAuth();
  const [serverError, setServerError] = useState('');

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  const onSubmit = async (data: FormValues) => {
    setServerError('');
    try {
      const user = await authService.signUp(data.email, data.fullName, data.password);
      auth.signIn(user);
      navigate('/client/dashboard');
    } catch (err) {
      setServerError(err instanceof Error ? err.message : 'Sign up failed. Please try again.');
    }
  };

  return (
    <div className="bg-bg-surface border border-border-default rounded-xl p-8 shadow-xl w-full">
      <h2 className="text-2xl font-bold text-text-primary mb-1">Create your account</h2>
      <p className="text-sm text-text-secondary mb-6">Start your onboarding journey with ClearPath</p>

      <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-4">
        <div>
          <TextInput
            label="Full name"
            placeholder="Jordan Lee"
            autoComplete="name"
            data-autofocus
            classNames={{
              label: 'text-text-secondary text-sm mb-1',
              error: 'text-danger text-xs mt-1',
            }}
            error={errors.fullName?.message}
            {...register('fullName')}
          />
        </div>

        <div>
          <TextInput
            label="Email address"
            placeholder="you@example.com"
            autoComplete="email"
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
            placeholder="Min. 8 characters"
            autoComplete="new-password"
            classNames={{
              label: 'text-text-secondary text-sm mb-1',
              error: 'text-danger text-xs mt-1',
            }}
            error={errors.password?.message}
            {...register('password')}
          />
        </div>

        <div>
          <PasswordInput
            label="Confirm password"
            placeholder="Repeat your password"
            autoComplete="new-password"
            classNames={{
              label: 'text-text-secondary text-sm mb-1',
              error: 'text-danger text-xs mt-1',
            }}
            error={errors.confirmPassword?.message}
            {...register('confirmPassword')}
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
          {isSubmitting ? 'Creating account…' : 'Create account'}
        </button>
      </form>

      <p className="mt-5 text-sm text-center text-text-secondary">
        Already have an account?{' '}
        <Link to="/auth/signin" className="text-primary hover:underline font-medium">
          Sign in
        </Link>
      </p>
    </div>
  );
}
