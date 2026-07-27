import { Runner, RunnerStatus } from './runner';
import { createNanoEvents } from 'nanoevents';

interface ParcoursEvents {
  'runner-update': (runnerId: number, reason: string) => void;
  'stats-change': (stats: any) => void;
}

export class ParcoursState {
  public readonly id: number;
  public readonly name: string;
  public runners: Map<number, Runner>;
  public emitter = createNanoEvents<ParcoursEvents>();

  constructor(id: number, name: string, runners: Map<number, Runner> = new Map()) {
    this.id = id;
    this.name = name;
    this.runners = runners;

    // Optionnel: Abonner chaque runner ajouté pour remonter les events
    // Mais souvent, le composant UI s'abonne directement au runner.
  }

  static fromRaw(data: any): ParcoursState {
    const map = new Map<number, Runner>();
    if (Array.isArray(data.inscriptions)) {
      for (const rData of data.inscriptions) {
        const runner = Runner.fromRaw(rData);
        map.set(runner.id, runner);
      }
    }
    return new ParcoursState(data.id, data.name, map);
  }

  addOrUpdateRunner(rawData: any): Runner {
    let runner = this.runners.get(rawData.id);

    if (!runner) {
      runner = Runner.fromRaw(rawData);
      this.runners.set(runner.id, runner);
    } else {
      // Mise à jour mutable des données si besoin (ex: refresh complet)
      // Ou on suppose que le flux SSE envoie des événements incrémentaux (addPassage)
      // Ici, on gère le cas où on reçoit un état complet à nouveau
      // Pour optimiser, on pourrait avoir une méthode updateFromRaw dans Runner
      runner = Runner.fromRaw(rawData); // Remplacement pour simplifier ici
      this.runners.set(runner.id, runner);
    }

    this.emitter.emit('runner-update', runner.id, 'data');
    this.emitter.emit('stats-change', this.stats);
    return runner;
  }

  get stats(): Record<RunnerStatus, number> & { total: number } {
    const stats: any = { pending: 0, running: 0, finished: 0, disqualified: 0, abandoned: 0, absent: 0, total: 0 };
    for (const r of this.runners.values()) {
      stats[r.status]++;
      stats.total++;
    }
    return stats;
  }

  get isLaunched(): boolean {
    return this.stats.pending !== this.stats.total;
  }

  get launchable(): boolean {
    return this.stats.pending !== 0
  }
}