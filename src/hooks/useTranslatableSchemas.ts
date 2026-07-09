import { TranslatableSchema } from '../lib/translationTypes'
import { useApiDataQuery } from '../utils/useApiDataQuery'

type SchemasResponse = {
    schemas: TranslatableSchema[]
}

// Module-level so the function identity is stable — TanStack Query then
// memoizes the result and consumers get a referentially stable array.
const selectTranslatable = (data: SchemasResponse): TranslatableSchema[] =>
    data.schemas.filter(
        (schema) => schema.translatable && schema.relativeApiEndpoint
    )

/**
 * Fetch the schemas that are translatable AND exposed on the API.
 * Note: the /api/schemas endpoint ignores the `filter` parameter, so
 * filtering happens client side.
 */
export const useTranslatableSchemas = () => {
    const {
        data: schemas,
        isLoading,
        error,
    } = useApiDataQuery<SchemasResponse, Error, TranslatableSchema[]>({
        queryKey: ['schemas', 'translatable'],
        query: {
            resource: 'schemas',
            params: {
                fields: 'plural,translatable,relativeApiEndpoint',
            },
        },
        cacheTime: Infinity,
        staleTime: Infinity,
        select: selectTranslatable,
    })

    return {
        schemas,
        isLoading,
        error,
    }
}
