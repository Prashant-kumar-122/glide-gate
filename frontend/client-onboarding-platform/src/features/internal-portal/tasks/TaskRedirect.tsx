import { useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { tasksService } from '../../../mocks/services/cases.service';

/**
 * Handles legacy / bookmarked URLs of the form /internal/tasks/:taskId.
 * Looks up the task, finds its parent caseId, and redirects to the case
 * detail page with the task pre-opened: /internal/cases/:caseId?task=:taskId
 */
export default function TaskRedirect() {
  const { taskId } = useParams<{ taskId: string }>();
  const navigate   = useNavigate();

  const { data: task, isLoading } = useQuery({
    queryKey: ['task', taskId],
    queryFn:  () => tasksService.getTaskById(taskId!),
    enabled:  !!taskId,
  });

  useEffect(() => {
    if (isLoading) return;
    if (task?.caseId) {
      navigate(`/internal/cases/${task.caseId}?task=${task.id}`, { replace: true });
    } else {
      navigate('/internal/dashboard', { replace: true });
    }
  }, [task, isLoading, navigate]);

  return (
    <div className="flex items-center justify-center min-h-64">
      <div className="animate-pulse h-6 w-48 bg-bg-elevated rounded" />
    </div>
  );
}
