import type { DateTime } from "luxon";

/**
Valid	          🟢 Vert	  Dossard valide, coureur autorisé, temps enregistré avec succès en BDD.
Invalid Bib	    🔴 Rouge	Le numéro de dossard n’existe pas dans la liste des participants de cet événement.
Bib Not Started	🟠 Orange	Le dossard est valide, mais le coureur n’a pas encore été enregistré au départ (Start). Impossible de valider un intermédiaire/arrivée avant le départ.
Duplicate	      🟣 Violet	Explication : Le système a détecté que ce dossard a déjà été chronométré à ce même point de contrôle (Stand) avec un temps très proche (ex: < 2 secondes). Cela évite les doubles saisies accidentelles.
Manual Override	🔵 Bleu	  Explication : Ce temps a été modifié manuellement par un administrateur après coup (ex: correction d’une erreur de saisie, ajout d’un temps oublié). Il se distingue des temps "automatiques" pour l’audit.
Server Error	  ⚫ Gris   Foncé	Erreur technique (500, 400, Timeout). Le temps n’a pas pu être traité. Nécessite une intervention.
Pending Server	⚪ Gris   Clair / Clignotant	Statut temporaire (Optimistic UI). La requête a été envoyée, on attend la confirmation du serveur via SSE.
*/


/** */
export interface TimingAction {
  id: number // int (positive -> synced with server, negative -> temporary local id)
  bib: number;
  timestamp: DateTime;
  key: string;
  last_modified: DateTime;
  status: 'pending' | 'synced' | 'error' | 'user' | 'alert';
  error_type?: 'invalid_bib' | 'bib_not_started' | 'server' | 'duplicate' | undefined;
  error_message?: string
}

export interface SyncState {
  is_online: boolean;
  queue_length: number;
  last_sync: number | null;
}