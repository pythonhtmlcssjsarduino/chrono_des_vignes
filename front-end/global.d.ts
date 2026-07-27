declare module "inline:*" {
  const content: string;
  export default content;
}

/**
 * Génère une URL d'API basée sur les routes Flask.
 * L'implémentation est injectée par le plugin esbuild.
 * 
 * @param package - Section de l'API (ex: 'parcours', 'dossard', 'chronometrage')
 * @param version - Version de l'API (ex: 'v1', 'v2')
 * @param endpoint - Chemin de l'endpoint (ex: '/liste', '/user/${id}')
 * @returns L'URL complète résolue (ex: '/api/parcours/v1/liste')
 */
function apiUrl(
  package: string,
  version: string,
  endpoint: string
): string;