import { DateTime } from 'luxon';
import { TimingAction } from './types';

export interface StorageService {
  VALIDATED_KEY: string; // template string for the validated queue key ({{key}} will be replaced by the actual key)
  PENDING_KEY: string;  // template string for the pending times key ({{key}} will be replaced by the actual key)
  /** Sauvegarde la file d'attente complète */
  saveValidatedQueue(actions: TimingAction[], key: string): Promise<void>;

  /** Charge la file d'attente au démarrage */
  loadValidatedQueue(key: string): Promise<TimingAction[]>;

  /** Sauvegarde les temps en attente */
  savePendingTimes(times: DateTime[], key: string): Promise<void>;

  /** Charge les temps en attente au démarrage */
  loadPendingTimes(key: string): Promise<DateTime[]>;

  /** Nettoie les actions synchronisées (optionnel, pour garder le storage léger) */
  clearSynced(): Promise<void>;
}