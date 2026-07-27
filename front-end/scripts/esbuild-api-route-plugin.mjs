import fs from 'fs';
import path from 'path';

export default function esbuildApiRoutePlugin() {
    return {
        name: 'esbuild-api-route-plugin',
        setup(build) {
            const regex = /apiUrl\(\s*['"`]([^'"`]+)['"`]\s*,\s*['"`]([^'"`]+)['"`]\s*,\s*['"`]([^'"`]+)['"`]\s*\)/g;

            build.onLoad({ filter: /\.ts$/ }, async (args) => {
                let contents = await fs.promises.readFile(args.path, 'utf8');
                let match;
                let hasChanges = false;
                let newContents = contents;

                // On parcourt toutes les occurrences
                // Note: Pour un remplacement parfait avec regex complexe, on utilise une fonction de remplacement
        
                newContents = contents.replace(regex, (match, section, version, endpoint) => {
                    hasChanges = true;
                    console.log(`🔍 Trouvé apiUrl(${section}, ${version}, ${endpoint}) dans ${args.path}`);

                    // Logique de reconstruction de la clé Flask
                    // Nettoie l'endpoint : '/liste' -> 'liste', '/user/${id}' -> 'user_${id}'
                    //let cleanEnd = endpoint.replace(/^\//, '').replace(/\//g, '_').replace(/\$\{/g, '').replace(/\}/g, '');
                    //let endpointKey = `api.${section}.${cleanEnd}`;

                    // Recherche dans les routes Flask
                    //let foundUrl = flaskRoutes[endpointKey];

                    //if (!foundUrl) {
                    //    // Tentative alternative si la convention de nommage varie
                    //    // Ex: chercher juste par chemin si le nom de fonction est différent
                    //    // Ici on fait une recherche brute dans les valeurs pour trouver celle qui correspond au pattern
                    //    const targetPattern = `/api/${section}/${version}${endpoint}`;
                    //    // Simple fallback construction si pas trouvé
                    //    foundUrl = `/api/${section}/${version}${endpoint}`;
                    //    console.warn(`⚠️  Route non trouvée dans Flask pour "${endpointKey}". Utilisation du fallback: ${foundUrl}`);
                    //} else {
                    //    // Si trouvé, on reconstruit l'URL avec les variables TS si présentes
                    //    // Flask donne: /api/parcours/${id}
                    //    // TS donne: endpoint = '/${id}'
                    //    // Le résultat doit préserver les ${...} du TS si ils correspondent
                    //    foundUrl = foundUrl; // Déjà au bon format ${id}
                    //}

                    return `\`/api/${version}/${section}${endpoint}\``;
                });

                if (hasChanges) {
                    return { contents: newContents, loader: 'ts' };
                }

                return null; // Pas de changement, on laisse esbuild gérer normalement
            });
        }}}