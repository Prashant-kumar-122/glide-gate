import type { DocumentOut, OcrField, OcrResult } from '@/lib/api'
import type { QuestionSchemaItem } from '@/hooks/useDocuments'
import { useUpdateCollectedField } from '@/hooks/useDocuments'

export function useDocumentPrefill(caseId: string | null) {
  const { mutateAsync } = useUpdateCollectedField(caseId)

  async function prefill(
    docs: DocumentOut[],
    schema: QuestionSchemaItem[],
  ): Promise<{ count: number }> {
    const schemaKeySet = new Set(schema.map((f) => f.question_key))
    const toUpdate: { questionKey: string; value: string }[] = []
    const seen = new Set<string>()

    for (const doc of docs) {
      const ocr = doc.ocr_result as OcrResult | null | undefined
      for (const field of ocr?.fields ?? []) {
        if (
          field.confidence >= 0.7 &&
          schemaKeySet.has(field.key) &&
          !seen.has(field.key)
        ) {
          seen.add(field.key)
          toUpdate.push({ questionKey: field.key, value: field.value })
        }
      }
    }

    const results = await Promise.allSettled(
      toUpdate.map(({ questionKey, value }) => mutateAsync({ questionKey, value })),
    )
    return { count: results.filter((r) => r.status === 'fulfilled').length }
  }

  async function prefillFromFields(
    fields: OcrField[],
    schema: QuestionSchemaItem[],
  ): Promise<{ count: number }> {
    const schemaKeySet = new Set(schema.map((f) => f.question_key))
    const toUpdate: { questionKey: string; value: string }[] = []
    const seen = new Set<string>()

    for (const field of fields) {
      if (
        field.confidence >= 0.7 &&
        schemaKeySet.has(field.key) &&
        !seen.has(field.key)
      ) {
        seen.add(field.key)
        toUpdate.push({ questionKey: field.key, value: field.value })
      }
    }

    const results = await Promise.allSettled(
      toUpdate.map(({ questionKey, value }) => mutateAsync({ questionKey, value })),
    )
    return { count: results.filter((r) => r.status === 'fulfilled').length }
  }

  return { prefill, prefillFromFields }
}
