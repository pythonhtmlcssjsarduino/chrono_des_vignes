import { DateTime } from 'luxon';

export class Passage {
  public readonly id: number;
  public readonly standId: number;
  public readonly standName: string;
  public readonly timestamp: DateTime;
  public readonly distanceKm: number | null;
  public readonly deltaMs: number | null;
  public readonly keyId: string | null;
  public readonly keyName: string | null;

  constructor(
    id: number,
    standId: number,
    standName: string,
    timestamp: DateTime,
    distanceKm: number | null,
    deltaMs: number | null,
    keyId: string | null,
    keyName: string | null
  ) {
    this.id = id;
    this.standId = standId;
    this.standName = standName;
    this.timestamp = timestamp;
    this.distanceKm = distanceKm;
    this.deltaMs = deltaMs;
    this.keyId = keyId;
    this.keyName = keyName;
  }

  static fromRaw(data: any): Passage {
    console.log('Passage.fromRaw', data.stand.name);
    return new Passage(
      data.id,
      data.stand.id,
      data.stand.name,
      DateTime.fromISO(data.time_stamp),
      data.distance_km ?? null,
      data.delta_ms ?? null,
      data.key?.id ?? null,
      data.key?.name ?? null
    );
  }

  get timeString(): string {
    return this.timestamp.toFormat(' HH:mm:ss');
  }
}