import { DateTime } from 'luxon';
import { StorageService } from './storage.service';
import { TimingAction, SyncState } from './types';
import { createNanoEvents } from 'nanoevents';
import { LocalStorageService } from './storage-local.impl';
import { BlackBoxLogService } from './BlackBoxLog';


interface SyncEngineEvents {
  update: (state: SyncState) => void;
  QueueUpdated: (queue: TimingAction[]) => void;
  PendingTimesUpdated: (times: DateTime[]) => void;
}


function getRandomNegId(): number {
  let digit = 20
  return -Math.floor(Math.random() * 10 ** digit)
}

export class SyncEngine {
  private queue: TimingAction[] = [];
  getQueue() {
    return this.queue;
  }
  private pendingTimes: DateTime[] = [];
  private isProcessing: boolean = false
  private apiUrl: string = apiUrl('chrono', 'v1', '/passages'); // À adapter selon ton config Flask
  private eventEmitter = createNanoEvents<SyncEngineEvents>();
  KEY!: string;
  public logger!: BlackBoxLogService;


  on<K extends keyof SyncEngineEvents>(event: K, callback: SyncEngineEvents[K]) {
    return this.eventEmitter.on(event, callback);
  }

  async init(key: string) {
    this.logger = new BlackBoxLogService(key);
    this.KEY = key
    // 1. Charger la file d'attente depuis le stockage local
    await this.loadAndSyncQueue();
    this.pendingTimes = await StorageService.loadPendingTimes(this.KEY);
    this.eventEmitter.emit('PendingTimesUpdated', this.pendingTimes);

    // 2. Tenter de synchroniser tout ce qui est en attente
    if (navigator.onLine) {
      this.processQueue();
    }

    // 3. Écouter les événements réseau
    window.addEventListener('online', () => this.processQueue());
    window.addEventListener('offline', () => this.notifyUpdate());
  }

  async loadAndSyncQueue() {
    const local_queue = await StorageService.loadValidatedQueue(this.KEY);
    const response = await fetch(apiUrl('chrono', 'v1', `/passages/${this.KEY}`), {
      method: 'GET'
    });
    if (!response.ok) {
      console.error('Erreur récupération queue serveur', response.status);
      this.queue = local_queue; // fallback to local queue
      this.notifyUpdate();
      this.eventEmitter.emit('QueueUpdated', this.queue);
      return;
    }
    const server_queue = await response.json();

    // Fusionner les deux queues, en priorisant les actions locales (non synchronisées)
    const mergedQueue: TimingAction[] = [];
    const serverQueueMap = new Map<number, TimingAction>();
    for (const action of server_queue) {
      serverQueueMap.set(action.id, LocalStorageService.deserializeTimingAction(action));
    }

    for (const localAction of local_queue) {
      if (localAction.status === 'pending' || localAction.status === 'error' || localAction.status === 'user') {
        mergedQueue.push(localAction);
      } else if (serverQueueMap.has(localAction.id)) {
        mergedQueue.push(serverQueueMap.get(localAction.id)!);
        serverQueueMap.delete(localAction.id);
      }
    }

    // Ajouter les actions serveur restantes qui n'étaient pas dans la queue locale
    for (const remainingServerAction of serverQueueMap.values()) {
      mergedQueue.push(remainingServerAction);
    }

    this.queue = mergedQueue;
    await this.persistQueue();

    this.notifyUpdate();
    this.eventEmitter.emit('QueueUpdated', this.queue);
  }

  /** Ajoute une action à la file (appelé par les composants lors d'une saisie) */
  async addAction(bib: number, timestamp: DateTime) {
    const action: TimingAction = {
      id: getRandomNegId(),
      bib,
      timestamp,
      key: this.KEY,
      last_modified: DateTime.now(),
      status: 'pending',
    };

    this.logger.log('timingaction', action); // Log dans le BlackBox

    // Optimistic UI: On ajoute à la file locale immédiatement
    this.queue.unshift(action); // Plus récent en haut
    await this.persistQueue();
    this.notifyUpdate();
    this.eventEmitter.emit('QueueUpdated', this.queue);

    // Tentative d'envoi immédiate si en ligne
    if (navigator.onLine) {
      this.processQueue();
    }

    return action;
  }

  addPendingTime(time: DateTime) {
    this.pendingTimes.unshift(time);
    this.eventEmitter.emit('PendingTimesUpdated', this.pendingTimes);
    void StorageService.savePendingTimes(this.pendingTimes, this.KEY);
    this.logger.log('pendingtime', { timestamp: time });
  }

  popLastPendingTime() {
    if (this.pendingTimes.length > 0) {
      const removedTime = this.pendingTimes.shift(); // Retire le premier (le plus récent)
      this.eventEmitter.emit('PendingTimesUpdated', this.pendingTimes);
      void StorageService.savePendingTimes(this.pendingTimes, this.KEY);
      return removedTime;
    }
  }

  /** Traite la file d'attente une par une */
  private async processQueue() {
    if (this.isProcessing || !navigator.onLine) return;
    this.isProcessing = true;

    // Filtrer les actions pending ou error (à retry)
    const pendingActions = this.queue.filter(a => a.status == 'error' || a.status == 'pending');

    for (const action of pendingActions) {
      await this.processAction(action);

      // Sauvegarde l'état mis à jour après chaque action
      await this.persistQueue();
      this.notifyUpdate();
      this.eventEmitter.emit('QueueUpdated', this.queue);

      // Petite pause pour ne pas flood le serveur
      await new Promise(r => setTimeout(r, 200));
    }

    this.isProcessing = false;

    // Nettoyage optionnel des éléments syncés vieux de plus de 24h (pour ne pas remplir le localStorage)
    // await this.cleanupOldSynced(); 
  }

  private async processAction(action: TimingAction) {
    const response = await fetch(this.apiUrl, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(action)
    });
    const old_id = action.id; // Sauvegarde l'ancien ID pour le log
    if (!response.ok) {
      action.status = 'error';
      action.error_type = 'server';
      action.error_message = `HTTP ${response.status}`;
    } else {
      const data = await response.json();

      Object.assign(action, LocalStorageService.deserializeTimingAction(data.action));
      if (old_id !== action.id) {
        this.logger.log('idupdate', { old_id, new_id: action.id });
      }
    }
  }

  private async persistQueue() {
    await StorageService.saveValidatedQueue(this.queue, this.KEY);
    // Optionnel: sauvegarder aussi dans l'audit log complet
    // await StorageService.saveAuditLog(this.queue); 
  }

  private notifyUpdate() {
    this.eventEmitter.emit('update', {
      is_online: navigator.onLine,
      queue_length: this.queue.filter(a => a.status == 'error' || a.status == 'pending').length,
      last_sync: Date.now()
    });
  }
}