import { DateTime, Duration } from 'luxon';
import { Passage } from './passage';
import { createNanoEvents } from 'nanoevents';

export type RunnerStatus =
  | 'pending' | 'running' | 'finished'
  | 'disqualified' | 'abandoned' | 'absent';

// Événements émis par cette instance
export interface RunnerEvents {
  'update': (reason: 'passage' | 'status' | 'start' | 'data') => void;
}

export class Runner {
  public readonly id: number;
  public readonly bibNumber: string;
  public readonly firstName: string;
  public readonly lastName: string;

  // État mutable
  public passages: Passage[];
  public statusOverride: RunnerStatus | null;

  // Bus d'événements propre à cette instance
  public emitter = createNanoEvents<RunnerEvents>();
  public on<K extends keyof RunnerEvents>(event: K, callback: RunnerEvents[K]) {
    return this.emitter.on(event, callback);
  }

  constructor(
    id: number,
    bibNumber: string,
    firstName: string,
    lastName: string,
    passages: Passage[] = [],
    statusOverride: RunnerStatus | null = null
  ) {
    this.id = id;
    this.bibNumber = bibNumber;
    this.firstName = firstName;
    this.lastName = lastName;
    this.passages = passages; // Mutable array
    this.statusOverride = statusOverride;
  }

  static fromRaw(data: any): Runner {
    const passages = (data.passages || []).map((p: any) => Passage.fromRaw(p)) as Passage[];
    // Tri initial
    passages.sort((a, b) => a.timestamp.valueOf() - b.timestamp.valueOf());

    return new Runner(
      data.id,
      data.bib_number,
      data.first_name,
      data.last_name,
      passages,
      data.status || null
    );
  }

  // --- Getters Calculés (Toujours à jour) ---

  get status(): RunnerStatus {
    if (this.statusOverride) return this.statusOverride;
    if (this.passages.length === 0) return 'pending';

    const last = this.passages[this.passages.length - 1];
    if (last.keyName === 'FINISH' || last.standName.toLowerCase().includes('finish')) {
      return 'finished';
    }
    return 'running';
  }

  get startTime(): DateTime | null {
    return this.passages.length > 0 ? this.passages[0].timestamp : null;
  }

  get elapsedTime(): Duration | null {
    const start = this.startTime;
    if (!start) {
      console.warn('start is null');
      return null
    };
    // Si fini, on fige au temps de fin
    if (this.status === 'finished' && this.passages.length > 0) {
      // Si le dernier passage est l'arrivée
      return this.passages[this.passages.length - 1].timestamp.diff(start);
    }
    return DateTime.now().diff(start);
  }

  get lastPassage(): Passage | null {
    return this.passages.length > 0 ? this.passages[this.passages.length - 1] : null;
  }

  get firstPassage(): Passage | null {
    return this.passages.length > 0 ? this.passages[0] : null;
  }

  // --- Méthodes Mutables (Modifient l'état et émettent) ---

  addPassage(passage: Passage): void {
    // Insertion triée (ou push si on est sûr que c'est le dernier)
    // Pour la perf, si on sait que c'est chronologique, on fait push()
    this.passages.push(passage);
    // Optionnel: tri de sécurité si le flux SSE peut être désordonné
    // this.passages.sort((a, b) => a.timestamp.valueOf() - b.timestamp.valueOf());

    this.emitter.emit('update', 'passage');
    console.log('pssage addid', passage);

    if (this.passages.length == 1) {
      this.setStatus('running')
      this.emitter.emit('update', 'start')
    }
  }

  setStatus(newStatus: RunnerStatus | null): void {
    console.log('new status', this.bibNumber, newStatus);

    this.statusOverride = newStatus;
    this.emitter.emit('update', 'status');
  }

  // Méthode utilitaire pour forcer un refresh si besoin externe
  notifyChange(): void {
    this.emitter.emit('update', 'data');
  }
}