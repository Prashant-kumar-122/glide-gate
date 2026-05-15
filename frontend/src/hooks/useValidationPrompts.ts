import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type { ValidationPrompt } from '@/lib/api'

const CATEGORIES = ['identity', 'financial', 'legal', 'insurance', 'compliance', 'entity'] as const
const PROMPTS_QK = ['admin', 'validation-prompts'] as const

const DEFAULTS: Record<string, ValidationPrompt> = {
  identity: {
    category: 'identity',
    goal: 'Verify identity document authenticity and completeness',
    factors: ['Document not expired', 'Photo clarity', 'Name matches case', 'DOB matches case', 'MRZ/barcode valid'],
  },
  financial: {
    category: 'financial',
    goal: 'Confirm financial document accuracy and recency',
    factors: ['Issued within 3 months', 'Account holder name present', 'Account number visible', 'Institution letterhead'],
  },
  legal: {
    category: 'legal',
    goal: 'Validate legal document completeness and signatures',
    factors: ['All pages present', 'Client signature', 'Date signed', 'Notarisation if required'],
  },
  insurance: {
    category: 'insurance',
    goal: 'Confirm insurance coverage details and validity',
    factors: ['Policy number present', 'Coverage dates valid', 'Beneficiary named', 'Policy type confirmed'],
  },
  compliance: {
    category: 'compliance',
    goal: 'Check compliance declarations are complete and current',
    factors: ['Declaration date current', 'Client signature present', 'Advisor attestation', 'Regulatory version'],
  },
  entity: {
    category: 'entity',
    goal: 'Validate entity documentation for onboarding',
    factors: ['Company registration number', 'Directors listed', 'Good standing certificate', 'Incorporation date'],
  },
}

export function useValidationPrompts() {
  return useQuery<ValidationPrompt[]>({
    queryKey: PROMPTS_QK,
    queryFn: async () => {
      const results = await Promise.allSettled(
        CATEGORIES.map((cat) =>
          api.get(`/admin/validation-prompts/${cat}`).then((r) => r.data as ValidationPrompt),
        ),
      )
      return results.map((r, i) =>
        r.status === 'fulfilled' ? r.value : DEFAULTS[CATEGORIES[i]],
      )
    },
    staleTime: 120_000,
    placeholderData: CATEGORIES.map((cat) => DEFAULTS[cat]),
  })
}

export function useUpdateValidationPrompt() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ category, prompt }: { category: string; prompt: Partial<ValidationPrompt> }) =>
      api.put(`/admin/validation-prompts/${category}`, prompt).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: PROMPTS_QK })
    },
  })
}
