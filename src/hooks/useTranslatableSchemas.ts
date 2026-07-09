import { TranslatableSchema } from '../lib/translationTypes'
import { useApiDataQuery } from '../utils/useApiDataQuery'

type SchemasResponse = {
    schemas: TranslatableSchema[]
}

/**
 * Fetch the schemas that are translatable AND exposed on the API.
 * Note: the /api/schemas endpoint ignores the `filter` parameter, so
 * filtering happens client side.
 */
export const useTranslatableSchemas = () => {
    const { data, isLoading, error } = useApiDataQuery<SchemasResponse>({
        queryKey: ['schemas', 'translatable'],
        query: {
            resource: 'schemas',
            params: {
                fields: 'plural,translatable,relativeApiEndpoint',
            },
        },
        cacheTime: Infinity,
        staleTime: Infinity,
    })

    return {
        schemas: data?.schemas.filter(
            (schema) => schema.translatable && schema.relativeApiEndpoint
        ),
        isLoading,
        error,
    }
}
