import type { DocumentOut, OcrField, OcrResult } from '@/lib/api'
import type { QuestionSchemaItem } from '@/hooks/useDocuments'
import { useUpdateCollectedField } from '@/hooks/useDocuments'
import { normalizeDateToISO } from '@/lib/dateUtils'

export function useDocumentPrefill(caseId: string | null) {
  const { mutateAsync } = useUpdateCollectedField(caseId)

  async function prefill(
    docs: DocumentOut[],
    schema: QuestionSchemaItem[],
  ): Promise<{ count: number }> {
    const schemaMap = new Map(schema.map((f) => [f.question_key, f]))
    const toUpdate: { questionKey: string; value: string }[] = []
    const seen = new Set<string>()

    for (const doc of docs) {
      const ocr = doc.ocr_result as OcrResult | null | undefined
      for (const field of ocr?.fields ?? []) {
        if (
          field.confidence >= 0.7 &&
          schemaMap.has(field.key) &&
          !seen.has(field.key)
        ) {
          seen.add(field.key)
          const isDate = schemaMap.get(field.key)?.field_type === 'date'
          toUpdate.push({ questionKey: field.key, value: isDate ? normalizeDateToISO(field.value) : field.value })
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
    const schemaMap = new Map(schema.map((f) => [f.question_key, f]))
    const toUpdate: { questionKey: string; value: string }[] = []
    const seen = new Set<string>()

    for (const field of fields) {
      if (
        field.confidence >= 0.7 &&
        schemaMap.has(field.key) &&
        !seen.has(field.key)
      ) {
        seen.add(field.key)
        const isDate = schemaMap.get(field.key)?.field_type === 'date'
        toUpdate.push({ questionKey: field.key, value: isDate ? normalizeDateToISO(field.value) : field.value })
      }
    }

    const results = await Promise.allSettled(
      toUpdate.map(({ questionKey, value }) => mutateAsync({ questionKey, value })),
    )
    return { count: results.filter((r) => r.status === 'fulfilled').length }
  }

  return { prefill, prefillFromFields }
}
