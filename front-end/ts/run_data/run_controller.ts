import { createNanoEvents, EmitterMixin } from 'nanoevents';
import { DateTime } from 'luxon';
import { ParcoursState } from './parcours_state';
import { Runner } from './runner';
import { Passage } from './passage';

// --- Types d'événements globaux émis par le gestionnaire ---
export interface GestionEvents {
  /** Déclenché quand un parcours entier est chargé ou rafraîchi */
  'parcours:loaded': (parcoursId: number) => void;

  /** Déclenché quand la connexion SSE change d'état */
  'sse:status': (connected: boolean) => void;

  /** Tick global pour l'animation des chronos (émis ~60fps ou 1fps) */
  'tick': (now: DateTime) => void;

  /** Erreur globale (réseau, API) */
  'error': (message: string) => void;
}

export class RunControllerM {
  // Stockage des états (Mutable)
  private parcoursMap: Map<number, ParcoursState> = new Map();

  // Configuration
  private readonly editionId: number;
  private readonly eventId: number;

  // SSE
  private eventSource: EventSource | null = null;

  // Tick Loop
  private tickTimer: number | null = null;
  private isTicking: boolean = false;

  // Bus d'événements global
  public emitter = createNanoEvents<GestionEvents>();
  public on<K extends keyof GestionEvents>(event: K, callback: GestionEvents[K]) {
    return this.emitter.on(event, callback);
  }

  constructor(editionId: number, eventId: number) {
    this.editionId = editionId;
    this.eventId = eventId;

    void this.loadInitialData();
    //this.startTickLoop();
  }

  // ========================================================================
  // 1. INITIALISATION & CHARGEMENT
  // ========================================================================

  /**
   * Charge l'état initial de tous les parcours via l'API REST.
   * Doit être appelé avant de démarrer le SSE.
   */
  async loadInitialData(): Promise<void> {
    try {
      const response = await fetch(apiUrl('run_control', "v1", `/get_edition_data/${this.eventId}/${this.editionId}`));
      if (!response.ok) throw new Error(`HTTP ${response.status}`);

      const data = await response.json();
      // data est attendu comme un tableau de parcours bruts
      data.parcours_version.forEach((parcoursData: any) => {
        const parcours = ParcoursState.fromRaw(parcoursData);
        this.parcoursMap.set(parcours.id, parcours);
        this.emitter.emit('parcours:loaded', parcours.id);
      });
    } catch (err) {
      console.error('Failed to load initial data', err);
      this.emitter.emit('error', 'Impossible de charger les données initiales');
      throw err;
    }
  }

  /**
   * Démarre la connexion SSE et la boucle de temps.
   */
  startRealTimeSync(): void {
    if (this.eventSource) return; // Déjà connecté

    this.eventSource = new EventSource(`/stream?channel=run_control_${this.editionId}_${this.eventId}`);

    this.eventSource.addEventListener('open', () => {
      console.log('SSE conneected');
      this.startTickLoop()
      this.emitter.emit('sse:status', true);
    })

    this.eventSource.onerror = () => {
      this.emitter.emit('sse:status', false);
      console.warn('SSE Connection lost. Reconnecting...');
      // EventSource gère la reconnexion auto, mais on peut ajouter une logique custom si besoin
    };

    // Écouteurs dynamiques pour les événements serveur
    // Note: addEventListener est nécessaire car les types d'événements sont dynamiques
    this.eventSource.addEventListener('new_passage', (e) => this.handleSSE_Passage(e));
    this.eventSource.addEventListener('status_change', (e) => this.handleSSE_StatusChange(e));
    this.eventSource.addEventListener('parcours_stop', (e) => this.handleSSE_ParcoursStop(e));
  }

  stopRealTimeSync(): void {
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }
    this.emitter.emit('sse:status', false);
  }

  // ========================================================================
  // 2. GESTION DES ÉVÉNEMENTS SSE (MUTATIONS)
  // ========================================================================

  private handleSSE_Passage(event: MessageEvent): void {
    try {
      console.log('passage:', event);

      const data = JSON.parse(event.data);
      const parcours = this.parcoursMap.get(data.parcours_id);
      if (!parcours) return;

      const runner = parcours.runners.get(data.inscription.id);
      if (runner) {
        // Mutation directe de l'objet Runner
        runner.addPassage(Passage.fromRaw(data));
      }
    } catch (e) {
      console.error('Error parsing new_passage SSE', e);
    }
  }

  private handleSSE_StatusChange(event: MessageEvent): void {
    try {
      const data = JSON.parse(event.data);
      // data: { parcoursId, inscriptionId, status, endTime? }
      const parcours = this.parcoursMap.get(data.parcoursId);
      if (!parcours) return;

      const runner = parcours.runners.get(data.inscriptionId);
      if (runner) {
        // Mutation du statut
        runner.setStatus(data.status);
        // Si on a un endTime explicite et qu'il n'est pas dans les passages, 
        // il faudrait peut-être ajouter un passage fantôme ou gérer ça dans le getter.
        // Pour l'instant, setStatus suffit car le getter status utilise statusOverride.

        parcours.emitter.emit('stats-change', parcours.stats);
      }
    } catch (e) {
      console.error('Error parsing status_change SSE', e);
    }
  }

  private handleSSE_ParcoursStop(event: MessageEvent): void {
    try {
      const data = JSON.parse(event.data);
      // data: { parcoursId, timestamp, affectedRunners: [{id, status}] }
      const parcours = this.parcoursMap.get(data.parcoursId);
      if (!parcours) return;

      if (data.affectedRunners) {
        data.affectedRunners.forEach((r: any) => {
          const runner = parcours.runners.get(r.id);
          if (runner) {
            runner.setStatus(r.status);
          }
        });
      }
      parcours.emitter.emit('stats-change', parcours.stats);
    } catch (e) {
      console.error('Error parsing parcours_stop SSE', e);
    }
  }

  // ========================================================================
  // 3. ACTIONS UTILISATEUR (APPELS API)
  // ========================================================================

  /**
   * Lance tout un parcours (Batch Start).
   * Le serveur émettra ensuite un événement 'batch_start'.
   */
  async launchParcours(parcoursId: number): Promise<void> {
    const now = DateTime.now().toISO();
    try {
      const res = await fetch(apiUrl('run_control', "v1", `/launch_parcours/${this.eventId}/${this.editionId}/${parcoursId}`), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ timestamp: now })
      });
      if (!res.ok || (await res.json()).success == false) {
        throw new Error('Failed to launch parcours');
      }
      console.log('parcours launched', parcoursId);

      // On attend la confirmation via SSE pour mettre à jour l'UI (cohérence forte)
    } catch (err) {
      this.emitter.emit('error', 'Échec du lancement du parcours');
      throw err;
    }
  }

  /**
   * Démarre un coureur individuellement.
   */
  async startRunner(parcoursId: number, runnerId: number): Promise<void> {
    const now = DateTime.now().toISO();
    try {
      const res = await fetch(apiUrl('run_control', "v1", `/inscription/${this.eventId}/${this.editionId}/${runnerId}/start`), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ timestamp: now })
      });
      if (!res.ok) throw new Error('Failed to start runner');
      // Confirmation via SSE 'runner_start' attendue
    } catch (err) {
      this.emitter.emit('error', 'Échec du démarrage du coureur');
      throw err;
    }
  }

  /**
   * Arrête tout le parcours (marque les absents/abandons).
   */
  async stopParcours(parcoursId: number): Promise<void> {
    try {
      const res = await fetch(apiUrl('run_control', "v1", `/parcours/${this.eventId}/${this.editionId}/${parcoursId}/stop`), {
        method: 'POST'
      });
      if (!res.ok) throw new Error('Failed to stop parcours');
      // Confirmation via SSE 'parcours_stop' attendue
    } catch (err) {
      this.emitter.emit('error', 'Échec de l\'arrêt du parcours');
      throw err;
    }
  }

  /**
   * Action manuelle sur un coureur (Disqualify, Abandon, Finish).
   */
  async setRunnerStatus(runnerId: number, status: 'disqualified' | 'abandoned' | 'finished' | null): Promise<void> {
    try {
      const res = await fetch(apiUrl('run_control', "v1", `/inscription/${this.eventId}/${this.editionId}/${runnerId}/action`), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status })
      });
      if (!res.ok) throw new Error('Failed to update status');
      // Confirmation via SSE 'status_change' attendue
    } catch (err) {
      this.emitter.emit('error', `Échec de la mise à jour du statut (${status})`);
      throw err;
    }
  }

  // ========================================================================
  // 4. UTILITAIRES & ACCÈS AUX DONNÉES
  // ========================================================================

  getParcours(parcoursId: number): ParcoursState | undefined {
    return this.parcoursMap.get(parcoursId);
  }

  getAllParcours(): ParcoursState[] {
    return Array.from(this.parcoursMap.values());
  }

  getRunner(parcoursId: number, runnerId: number): Runner | undefined {
    return this.parcoursMap.get(parcoursId)?.runners.get(runnerId);
  }

  // Boucle de temps pour les chronos
  private startTickLoop(): void {
    if (this.isTicking) return;
    this.isTicking = true;

    const loop = () => {
      const now = DateTime.now();
      this.emitter.emit('tick', now);
      this.tickTimer = requestAnimationFrame(loop);
    };
    loop();
  }

  private stopTickLoop(): void {
    this.isTicking = false;
    if (this.tickTimer) {
      cancelAnimationFrame(this.tickTimer);
      this.tickTimer = null;
    }
  }


}