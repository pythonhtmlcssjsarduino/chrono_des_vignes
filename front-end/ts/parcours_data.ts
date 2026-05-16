import { createNanoEvents, Emitter } from "nanoevents"

export interface stand { id: number, name: string, lat: number, lng: number, ele: number, color: string, chrono: boolean }
export interface segment { id: number, start: number, to: number, trace: [number, number, number | null][], index: number }

export type Events = { [K in Ops]: (change: Extract<Changes, { op: K }>) => void; } & {
  'parcours:modifEnabled': (enabled: boolean) => void;
  'stand:selected': (id: number) => void;
  'segment:selected': (id: number) => void;
  'idsUpdated': (ids: Record<number, number>) => void;
  'stand:deleted': (id: number) => void
}

function getRandomNegId(): number {
  let digit = 20
  return -Math.floor(Math.random() * 10 ** digit)
}

// #region changes
interface changeSegmentModif { // modif segment
  op: 'segment:modif',
  id: number, // id du segment
  trace?: [number, number, number | null][]
}
interface changeStandModif { // modif segment
  op: 'stand:modif',
  id: number, // id du stand
  lat?: number,
  lng?: number,
  name?: string,
  ele?: number | '',
  color?: string,
  chrono?: boolean,
}
interface changeParcoursModif {
  op: 'parcours:modif',
  name?: string,
  versionDescription?: string,
  description?: string
}
type Changes = changeSegmentModif | changeStandModif | changeParcoursModif
type Ops = Changes['op']
// #endregion

export class ParcoursData {
  private eventEmitter: Emitter<Events>
  private _name: string;
  private _description: string;
  private _stands: StandData[];
  private _segments: SegmentData[];
  private changes: Changes[]
  private timoutId?: number
  private _parcoursModified: boolean = false
  constructor(
    readonly id: number,
    readonly event_id: number,
    name: string,
    description: string,
    readonly creation_date: Date,
    stands: ((parcours: ParcoursData) => StandData)[],
    segments: ((parcours: ParcoursData) => SegmentData)[],
    private _modif: boolean,
    readonly modif_allowed: boolean
  ) {
    this.changes = [];
    this.eventEmitter = createNanoEvents<Events>()
    this._name = name;
    this._description = description;
    this._stands = stands.map(stand => stand(this));
    this._segments = segments.map(segment => segment(this));

    document.addEventListener('keydown', e => {
      if (e.ctrlKey && e.key === 's') {
        // Prevent the Save dialog to open
        e.preventDefault();
        this.syncOps()
      }
    });

  }
  set parcoursModified(value: boolean) {
    this._parcoursModified = value || this._parcoursModified
  }
  get parcoursModified() {
    return this._parcoursModified
  }

  get stands(): StandData[] {
    return this._stands;
  }
  get segments(): SegmentData[] {
    return this._segments;
  }

  get name(): string {
    return this._name;
  }
  set name(value: string) {
    this._name = value;
  }
  get description(): string {
    return this._description;
  }
  set description(value: string) {
    this._description = value;
  }

  get_stand(id: number): StandData | undefined {
    return this._stands.find(stand => stand.id == id);
  }
  get_segment(id: number): SegmentData | undefined {
    return this._segments.find(segment => segment.id == id)
  }
  get_segment_from_index(index: number): SegmentData | undefined {
    return this._segments.find(segment => segment.index == index)
  }
  get_last_segment() {
    if (this._segments.length == 0) {
      return
    }
    return this._segments.reduce((previousSegment, segment) => previousSegment.index > segment.index ? previousSegment : segment)
  }
  get_last_stand() {
    if (this._segments.length == 0) {
      return this._stands.length == 1 ? this._stands[0] : undefined
    }
    return this.get_stand(this.get_last_segment()!.to)
  }

  on<E extends keyof Events>(event: E, callback: Events[E]) {
    return this.eventEmitter.on(event, callback)
  }

  get modif(): boolean {
    return this._modif
  }

  /** enable modification state and return the resulting state */
  enableModif() {
    this._modif = this.modif_allowed;
    this.eventEmitter.emit('parcours:modifEnabled', this._modif)
    return this._modif
  }

  /** disable modification state and return the resulting state */
  disableModif() {
    this._modif = false;
    this.eventEmitter.emit('parcours:modifEnabled', this._modif)
    return this._modif
  }

  /** toggle modification state and return the resulting state */
  toggleModif() {
    this._modif = !this._modif && this.modif_allowed;
    this.eventEmitter.emit('parcours:modifEnabled', this._modif)
    return this._modif
  }

  /**check if the parcours is empty (not edited) */
  isEmpty() {
    return this._stands.length == 0 && this._segments.length == 0
  }

  selectStand(id: number) {
    if (!this._modif) return
    this.eventEmitter.emit('stand:selected', id)
  }

  selectSegment(id: number) {
    if (!this._modif) return
    this.eventEmitter.emit('segment:selected', id)
  }

  segmentChange(id: number, trace: SegmentPoint[]) {
    if (!this._modif) return
    let change: Changes = {
      op: 'segment:modif',
      id: id,
      trace: trace
    }
    this.addOp(change)
  }

  private async commitOp(op: Changes) {

    const index = this.changes.findIndex(change => change.op === op.op && (!('id' in change && 'id' in op) || change.id === op.id))
    if (index != -1) {
      // fusionne (add or replace each new field)
      for (const [key, value] of Object.entries(op) as [keyof Changes, any][]) {
        if (value != undefined) {
          this.changes[index][key] = value;
        } else if (key != 'op') {
          delete this.changes[index][key];
        }
      }
    } else {
      this.changes.push(op);
    }

    clearTimeout(this.timoutId)
    this.timoutId = setTimeout(this.syncOps.bind(this), 5000);

  }

  private async syncOps() {

    if (this.parcoursModified) {
      // send the entire parcours
      this.changes = []
      const resp = await fetch(apiUrl('parcours', 'v1', `/update_parcours/${this.event_id}/${this.id}`), {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(this.toJson()),
      })

      const json = await resp.json();
      console.log(json);

      if (json.success) {
        this._parcoursModified = false
        this.updateIds(json.ids)
      }
    } else if (this.changes.length != 0) {
      const ops = [...this.changes]
      this.changes = []
      console.log('syncing', ops, this.parcoursModified);
      const resp = await fetch(apiUrl('parcours', 'v1', `/update_parcours/${this.event_id}/${this.id}`), {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(ops),
      })
      const json = await resp.json();
      console.log(json);
    }

  }
  toJson(): any {
    return {
      "creation_date": this.creation_date.toISOString(),
      "description": this.description,
      "id": this.id,
      "modif": this.modif,
      "modif_allowed": this.modif_allowed,
      "name": this.name,
      "segments": this.segments.map(segment => segment.toJson()),
      "stands": this.stands.map(stand => stand.toJson())
    }
  }
  toString(): string {
    return `ParcoursData(id=${this.id}, name=${this.name}, description=${this.description}, creation_date=${this.creation_date.toISOString()}, nb_stands=${this.stands.length}, nb_segments=${this.segments.length})`
  }

  /**update {old:new, ...} all ids (stands + segments) */
  private updateIds(ids: { [k: number]: number }) {
    this.eventEmitter.emit('idsUpdated', ids)
    this._stands.filter((stand) => stand.id < 0 && ids[stand.id]).forEach(stand => {
      stand.updateId(ids[stand.id])
    });
    this._segments.filter((stand) => stand.id < 0 && ids[stand.id]).forEach(stand => {
      stand.updateId(ids[stand.id])
    })
  }

  addOp(op: Changes) {
    void this.commitOp(op)
    this.eventEmitter.emit(op.op, op as any);
  }

  static async fetch(event_id: number, parcours_id: number): Promise<ParcoursData> {

    const url = apiUrl('parcours', 'v1', `/get_parcours/${event_id}/${parcours_id}`);

    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(`Response status: ${response.status}`);
    }

    const result = await response.json();
    return ParcoursData.fromJson(result);
  }

  static fromJson(data: any): ParcoursData {
    return new ParcoursData(data.id, data.event_id, data.name, data.description, new Date(data.creation_date), data.stands.map((stand: any) => StandData.fromJson(stand)), data.segments.map((segment: any) => SegmentData.fromJson(segment)), data.modif, data.modif_allowed);
  }

  static empty(): ParcoursData {
    return new ParcoursData(0, 0, "", "", new Date(), [], [], false, false);
  }

  createStand(lat: number, lng: number, chrono: boolean) {
    const tempId = getRandomNegId()
    const data = new StandData(this, tempId, '', lat, lng, chrono)
    this._stands.push(data)
    this.parcoursModified = true
    return data
  }

  createSegment(start: StandData, end: StandData, index: number) {
    const tempId = getRandomNegId()
    const data = new SegmentData(this, tempId, start.id, end.id, [], index)
    this._segments.push(data)
    this.parcoursModified = true
    return data
  }
  deleteStand(id: number) {
    this.eventEmitter.emit('stand:deleted', id)
    this._stands = this._stands.filter(stand => stand.id != id)
  }
}

type standEvent = {
  'selected': (selected: boolean) => void,
  'nameChanged': (name: string) => void,
  'latlngChanged': (lat: number, lng: number) => void,
  'chronoChanged': (chrono: boolean) => void,
  'colorChanged': (color: string) => void,
  'idUpdated': (newId: number) => void,
}

export class StandData {
  toJson(): any {
    return {
      "chrono": this.chrono,
      "color": this.color,
      "ele": this.ele,
      "id": this.id,
      "lat": this.lat,
      "lng": this.lng,
      "name": this.name
    }
  }
  private _name: string;
  private _lat: number;
  private _lng: number;
  private _ele: number | null;
  private _color: string;
  private _chrono: boolean;
  private _id: number
  private selected: boolean = false
  private eventEmitter = createNanoEvents<standEvent>()
  constructor(
    public parcours: ParcoursData,
    id: number,
    name: string,
    lat: number,
    lng: number,
    chrono: boolean = false,
    ele: number | null = null,
    color: string = '#00ff00',
  ) {
    this._id = id
    this._name = name;
    this._lat = lat;
    this._lng = lng;
    this._ele = ele;
    this._color = color;
    this._chrono = chrono


    parcours.on('stand:selected', id => {
      if (id == this.id && !this.selected) {
        this.eventEmitter.emit('selected', true)
        this.selected = true
      }
      else if (id != this.id && this.selected) {
        this.eventEmitter.emit('selected', false)
        this.selected = false
      }
    })
    parcours.on('segment:selected', id => {
      if (this.selected) {
        this.selected = false
        this.eventEmitter.emit('selected', false)
      }
    })
    parcours.on('parcours:modifEnabled', enabled => {
      if (!enabled) {
        this.selected = false
        this.eventEmitter.emit('selected', false)
      }
    })
  }
  on<E extends keyof standEvent>(event: E, callback: standEvent[E]) {
    return this.eventEmitter.on(event, callback)
  }
  get id(): number {
    return this._id
  }
  updateId(newId: number) {
    this._id = newId
    this.eventEmitter.emit('idUpdated', newId)
  }

  get name(): string {
    return this._name;
  }
  set name(value: string) {
    this._name = value;
    this.eventEmitter.emit('nameChanged', value)
    this.parcours.addOp({
      op: 'stand:modif',
      id: this.id,
      name: value
    })
  }
  get lat(): number {
    return this._lat;
  }
  set lat(value: number) {
    this._lat = value
    this.eventEmitter.emit('latlngChanged', value, this._lng)
    this.parcours.addOp({
      op: 'stand:modif',
      id: this.id,
      lat: value
    })
  }
  get lng(): number {
    return this._lng;
  }
  set lng(value: number) {
    this._lng = value
    this.eventEmitter.emit('latlngChanged', this._lat, value)
    this.parcours.addOp({
      op: 'stand:modif',
      id: this.id,
      lng: value
    })
  }
  get latlng() {
    return [this.lat, this.lng] as [number, number]
  }
  setLatLng(lat: number, lng: number) {
    this._lat = lat;
    this._lng = lng;
    this.eventEmitter.emit('latlngChanged', lat, lng)
    this.parcours.addOp({
      op: 'stand:modif',
      id: this.id,
      lat: lat,
      lng: lng
    })
  }
  get color(): string {
    return this._color;
  }
  set color(value: string) {
    this._color = value;
    this.eventEmitter.emit('colorChanged', value)
    this.parcours.addOp({
      op: 'stand:modif',
      id: this.id,
      color: value
    })
  }
  get ele(): number | null {
    return this._ele;
  }
  set ele(value: number | null) {
    this._ele = value;
  }
  get chrono(): boolean {
    return this._chrono;
  }
  set chrono(value: boolean) {
    this._chrono = value;
    this.eventEmitter.emit('chronoChanged', value)
    this.parcours.addOp({
      op: 'stand:modif',
      id: this.id,
      chrono: value
    })
  }
  static fromJson(data: any): (parcours: ParcoursData) => StandData {
    return (parcours: ParcoursData) => new StandData(parcours, data.id, data.name, data.lat, data.lng, data.chrono, data.ele, data.color);
  }
}
type segmentEvent = {
  'selected': (selected: boolean) => void
  'idUpdated': (newId: number) => void,
  'traceChanged': (trace: SegmentPoint[]) => void
}
export type SegmentPoint = [number, number, number | null]
export class SegmentData {
  toJson(): any {
    return {
      "id": this.id,
      "index": this.index,
      "start": this.start,
      "to": this.to,
      "trace": this.trace
    }
  }
  private _trace: SegmentPoint[]
  eventEmitter = createNanoEvents<segmentEvent>()

  private selected: boolean = false
  private _id: number
  private _to: number

  constructor(public parcours: ParcoursData, id: number, readonly start: number, to: number, trace: SegmentPoint[], readonly index: number) {
    this._trace = trace
    this._id = id
    this._to = to

    parcours.on('stand:selected', id => {
      if (this.selected) {
        this.selected = false
        this.eventEmitter.emit('selected', false)
      }
    })
    parcours.on('segment:selected', id => {
      if (id == this.id && !this.selected) {
        this.eventEmitter.emit('selected', true)
        this.selected = true
      }
      else if (id != this.id && this.selected) {
        this.eventEmitter.emit('selected', false)
        this.selected = false
      }
    })
    parcours.on('parcours:modifEnabled', enabled => {
      if (!enabled) {
        this.selected = false
        this.eventEmitter.emit('selected', false)
      }
    })
  }
  get to() {
    return this._to
  }
  updateEnd(endId: number) {
    this.parcours.parcoursModified = false
    this._to = endId
  }
  get id(): number {
    return this._id
  }
  updateId(newId: number) {
    this._id = newId
    this.eventEmitter.emit('idUpdated', newId)
  }

  get trace() {
    return this._trace
  }
  set trace(trace: (SegmentPoint | [number, number])[]) {
    this._trace = trace.map(point => [point[0], point[1], point[2] ?? null])
    this.parcours.segmentChange(this.id, this._trace)
    this.eventEmitter.emit('traceChanged', this._trace)
  }

  setTracePoint(index: number, point: SegmentPoint | [number, number]) {
    point = [point[0], point[1], point[2] ?? null]
    this._trace[index] = point
    this.parcours.segmentChange(this.id, this._trace)
    this.eventEmitter.emit('traceChanged', this._trace)
  }

  on<E extends keyof segmentEvent>(event: E, callback: segmentEvent[E]) {
    return this.eventEmitter.on(event, callback)
  }

  select() {
    this.parcours.selectSegment(this.id)
  }

  static fromJson(data: any): (parcours: ParcoursData) => SegmentData {
    return (parcours: ParcoursData) => new SegmentData(parcours, data.id, data.start, data.to, data.trace, data.index);
  }
}