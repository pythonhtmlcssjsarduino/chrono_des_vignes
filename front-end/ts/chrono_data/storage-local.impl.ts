import { DateTime } from 'luxon';
import { StorageService } from './storage.interface';
import { TimingAction } from './types';


export class LocalStorageService implements StorageService {
  VALIDATED_KEY = 'chrono_validated_queue_{{key}}';
  PENDING_KEY = 'chrono_pending_times_{{key}}';

  async saveValidatedQueue(actions: TimingAction[], key: string): Promise<void> {
    const serialized = actions.map(a => LocalStorageService.serializeTimingAction(a));
    localStorage.setItem(this.VALIDATED_KEY.replace('{{key}}', key), JSON.stringify(serialized));
  }
  async loadValidatedQueue(key: string): Promise<TimingAction[]> {
    const data = localStorage.getItem(this.VALIDATED_KEY.replace('{{key}}', key));
    if (!data) return [];
    try {
      const parsedData = JSON.parse(data);

      for (const action of parsedData) {
        if (action.payload && action.payload.timestamp) {
          action.payload.timestamp = DateTime.fromISO(action.payload.timestamp);
        }
        if (action.created_at) {
          action.created_at = DateTime.fromISO(action.created_at);
        }
      }

      if (!Array.isArray(parsedData)) return [];
      const actions = parsedData.map((o: any) => LocalStorageService.deserializeTimingAction(o));
      return actions;
    } catch (e) {
      console.error('Erreur lecture queue locale', e);
      return [];
    }
  }

  static serializeTimingAction(action: TimingAction): any {
    const serializeTimestamp = (v: any) => {
      if (DateTime.isDateTime(v)) return v.toISO();
      if (typeof v === 'string') return v;
      return v === undefined ? undefined : v;
    };

    return {
      ...action,
      timestamp: serializeTimestamp(action.timestamp),
      last_modified: serializeTimestamp(action.last_modified),
    };
  }

  static deserializeTimingAction(obj: any): TimingAction {
    const deserializeTimestamp = (v: any) => {
      if (DateTime.isDateTime(v)) return v;
      if (typeof v === 'string') {
        const dt = DateTime.fromISO(v);
        if (dt.isValid) return dt;
      }
      return v;
    }

    return {
      ...obj,
      timestamp: deserializeTimestamp(obj.timestamp),
      last_modified: deserializeTimestamp(obj.last_modified),
    } as TimingAction;
  }

  async savePendingTimes(times: DateTime[], key: string): Promise<void> {
    const isoTimes = times.map(t => t.toISO());
    localStorage.setItem(this.PENDING_KEY.replace('{{key}}', key), JSON.stringify(isoTimes));
  }

  async loadPendingTimes(key: string): Promise<DateTime[]> {
    const data = localStorage.getItem(this.PENDING_KEY.replace('{{key}}', key));
    if (!data) return [];
    try {
      const isoTimes: string[] = JSON.parse(data);
      return isoTimes.map(t => DateTime.fromISO(t));
    } catch (e) {
      console.error('Erreur lecture pending times locale', e);
      return [];
    }
  }

  async clearSynced(): Promise<void> {
    throw new Error('Méthode clearSynced non implémentée pour LocalStorageService');
  }
}