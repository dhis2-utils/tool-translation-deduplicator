/** @type {import('@dhis2/cli-app-scripts').D2Config} */
const config = {
    type: 'app',
    name: 'tool-translation-deduplicator',
    title: 'Translation Deduplication Tool',
    description:
        'Finds and removes duplicate translations in metadata objects.',
    minDHIS2Version: '2.40',

    entryPoints: {
        app: './src/App.tsx',
    },

    viteConfigExtensions: './viteConfigExtensions.mts',
}

module.exports = config
