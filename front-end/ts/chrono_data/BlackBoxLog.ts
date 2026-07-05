import { encode, decode } from '@msgpack/msgpack';
import { DateTime } from 'luxon';


export const type_map = {
  'timingaction': 0,
  'pendingtime': 1,
  'idupdate': 2,
  'bibupdate': 3,
  'timestampupdate': 4,
} as const;

export interface TimingActionLog {
  id: number;
  bib: number;
  timestamp: DateTime;
}
export interface PendingTimeLog {
  timestamp: DateTime;
}
export interface IdUpdateLog {
  old_id: number;
  new_id: number;
}
export interface bibUpdateLog {
  id: number;
  new_bib: number;
}
export interface timestampUpdateLog {
  id: number;
  new_timestamp: DateTime;
}

export interface BlackBoxLogEntry {
  'timingaction': TimingActionLog
  'pendingtime': PendingTimeLog
  'idupdate': IdUpdateLog
  'bibupdate': bibUpdateLog
  'timestampupdate': timestampUpdateLog
};


export class BlackBoxLogService {
  // NOTE: Pour de vrais gros logs, IndexedDB est mieux car localStorage a une limite de taille par clé.

  private LOG_KEY: string;

  constructor(key: string) {
    this.LOG_KEY = `chrono_blackbox_stream_${key}`;
  }

  private readonly serializers: {
    [K in keyof BlackBoxLogEntry]: (action: BlackBoxLogEntry[K]) => any[]
  } = {
      timingaction: (action) => {
        return [
          type_map.timingaction,
          action.id,
          action.bib,
          action.timestamp.toUnixInteger()
        ];
      },
      pendingtime: (action) => {
        return [
          type_map.pendingtime,
          action.timestamp.toUnixInteger()
        ];
      },
      idupdate: (action) => {
        return [
          type_map.idupdate,
          action.old_id,
          action.new_id
        ];
      },
      bibupdate: (action) => {
        return [
          type_map.bibupdate,
          action.id,
          action.new_bib
        ];
      },
      timestampupdate: (action) => {
        return [
          type_map.timestampupdate,
          action.id,
          action.new_timestamp.toUnixInteger()
        ];
      }
    }

  private deserialize(action: any): BlackBoxLogEntry[keyof BlackBoxLogEntry] & { type: string } | undefined {
    if (!Array.isArray(action) || action.length === 0) return undefined;
    switch (action[0]) {
      case type_map.timingaction:
        return {
          type: 'timingaction',
          id: action[1],
          bib: action[2],
          timestamp: DateTime.fromSeconds(action[3])
        }
      case type_map.pendingtime:
        return {
          type: 'pendingtime',
          timestamp: DateTime.fromSeconds(action[1])
        }
      case type_map.idupdate:
        return {
          type: 'idupdate',
          old_id: action[1],
          new_id: action[2]
        };
      case type_map.bibupdate:
        return {
          type: 'bibupdate',
          id: action[1],
          new_bib: action[2]
        };
      case type_map.timestampupdate:
        return {
          type: 'timestampupdate',
          id: action[1],
          new_timestamp: DateTime.fromSeconds(action[2])
        };
    }
  };

  log<k extends keyof BlackBoxLogEntry>(type: k, action: BlackBoxLogEntry[k]): void {
    void this.asyncAppendAction(this.serializers[type](action));
  }

  /**
   * APPEND PUR : Encode l'objet et l'ajoute à la fin du flux existant.
   * Aucune lecture, aucun décodage du passé.
   */
  private async asyncAppendAction(action: any): Promise<void> {
    // 1. Encoder l'objet seul en binaire
    const encodedData = encode(action);

    // 2. Créer un préfixe de 4 octets pour la longueur (Big Endian)
    const length = encodedData.length;
    const prefix = new Uint8Array(4);
    const view = new DataView(prefix.buffer);
    view.setUint32(0, length, false); // false = Big Endian

    // 3. Concaténer Préfixe + Data
    const newChunk = new Uint8Array(4 + length);
    newChunk.set(prefix, 0);
    newChunk.set(encodedData, 4);

    // 4. Récupérer le flux existant (si on est en LocalStorage Base64)
    // NOTE: Pour de vrais gros logs, IndexedDB est mieux car localStorage a une limite de taille par clé.
    const existingRaw = localStorage.getItem(this.LOG_KEY);
    let combinedBuffer: Uint8Array;

    if (existingRaw) {
      // Décoder le Base64 existant
      const binaryString = atob(existingRaw);
      const len = binaryString.length;
      const existingBytes = new Uint8Array(len);
      for (let i = 0; i < len; i++) {
        existingBytes[i] = binaryString.charCodeAt(i);
      }

      // Concaténer l'ancien + le nouveau chunk
      combinedBuffer = new Uint8Array(existingBytes.length + newChunk.length);
      combinedBuffer.set(existingBytes, 0);
      combinedBuffer.set(newChunk, existingBytes.length);
    } else {
      combinedBuffer = newChunk;
    }

    // 5. Ré-encoder en Base64 pour stockage (ou stocker blob si IndexedDB)
    // Conversion rapide Uint8Array -> Base64
    let binary = '';
    const chunkSize = 0x8000; // Pour éviter stack overflow sur gros fichiers
    for (let i = 0; i < combinedBuffer.length; i += chunkSize) {
      binary += String.fromCharCode.apply(null, Array.from(combinedBuffer.subarray(i, i + chunkSize)) as any);
    }

    localStorage.setItem(this.LOG_KEY, btoa(binary));
  }

  /**
   * LECTURE SÉQUENTIELLE : Pour replay ou débogage.
   * Lit tout le flux et retourne un tableau d'actions.
   */
  async readFullLog(): Promise<any[]> {
    const raw = localStorage.getItem(this.LOG_KEY);
    if (!raw) return [];

    // Décoder Base64 -> Uint8Array
    const binaryString = atob(raw);
    const bytes = new Uint8Array(binaryString.length);
    for (let i = 0; i < binaryString.length; i++) {
      bytes[i] = binaryString.charCodeAt(i);
    }

    const actions: any[] = [];
    let offset = 0;

    // Boucle de lecture séquentielle
    while (offset < bytes.length) {
      // 1. Lire les 4 octets de longueur
      if (offset + 4 > bytes.length) break; // Fin de fichier ou corruption

      const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
      const length = view.getUint32(offset, false); // Big Endian
      offset += 4;

      // 2. Vérifier qu'on a assez de données
      if (offset + length > bytes.length) {
        console.warn('Log corrompu ou incomplet à la fin.');
        break;
      }

      // 3. Extraire le chunk de données
      const chunk = bytes.subarray(offset, offset + length);
      offset += length;

      // 4. Décoder l'objet
      try {
        const action = decode(chunk) as number[];
        actions.push(this.deserialize(action));
      } catch (e) {
        console.error('Erreur décodage chunk à offset', offset, e);
        // On peut choisir de continuer ou stopper
      }
    }

    return actions;
  }

  async exportFullFile() {
    const data = await this.readFullLog();
    // Implémenter l'export du fichier complet
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    return blob;
  }

  /**
   * Exporte le fichier brut (la boîte noire telle quelle)
   */
  async exportRawFile(): Promise<Blob> {
    const raw = localStorage.getItem(this.LOG_KEY);
    if (!raw) return new Blob([]);

    // Reconvertir Base64 -> Binary Blob directement
    const binaryString = atob(raw);
    const len = binaryString.length;
    const bytes = new Uint8Array(len);
    for (let i = 0; i < len; i++) {
      bytes[i] = binaryString.charCodeAt(i);
    }

    return new Blob([bytes], { type: 'application/octet-stream' });
  }

  static async download(blob: Blob, filename: string) {
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  async clear() {
    localStorage.removeItem(this.LOG_KEY);
  }
}
