/** @type {import('@dhis2/cli-app-scripts').D2Config} */
const config = {
    type: 'app',
    name: 'tool-translation-deduplicator',
    title: 'Translation Deduplicator Tool',
    description:
        'Tool to identify and remove duplicate translation keys in metadata.',
    minDHIS2Version: '2.40',

    entryPoints: {
        app: './src/App.tsx',
    },

    viteConfigExtensions: './viteConfigExtensions.mts',
}

module.exports = config
