// node_modules/nanoevents/index.js
var createNanoEvents = () => ({
  emit(event, ...args) {
    for (let callbacks = this.events[event] || [], i = 0, length = callbacks.length; i < length; i++) {
      callbacks[i](...args);
    }
  },
  events: {},
  on(event, cb) {
    ;
    (this.events[event] ||= []).push(cb);
    return () => {
      this.events[event] = this.events[event]?.filter((i) => cb !== i);
    };
  }
});

// ts/parcours_data.ts
var linearChanges = [];
var ParcoursData = class _ParcoursData {
  constructor(id, name, description, creation_date, stands, segments, _modif, modif_allowed) {
    this.id = id;
    this.creation_date = creation_date;
    this._modif = _modif;
    this.modif_allowed = modif_allowed;
    this.changes = [];
    this.commitChanges = [];
    this.eventEmitter = createNanoEvents();
    this._name = name;
    this._description = description;
    this._stands = stands.map((stand) => stand(this));
    this._segments = segments.map((segment) => segment(this));
  }
  get stands() {
    return this._stands;
  }
  get segments() {
    return this._segments;
  }
  get name() {
    return this._name;
  }
  set name(value) {
    this._name = value;
  }
  get description() {
    return this._description;
  }
  set description(value) {
    this._description = value;
  }
  get_stand(id) {
    return this._stands.find((stand) => stand.id == id);
  }
  on(event, callback) {
    return this.eventEmitter.on(event, callback);
  }
  get modif() {
    return this._modif;
  }
  enableModif() {
    this._modif = this.modif_allowed;
    this.eventEmitter.emit("parcours:modifEnabled", this._modif);
    return this._modif;
  }
  disableModif() {
    this._modif = false;
    this.eventEmitter.emit("parcours:modifEnabled", this._modif);
    return this._modif;
  }
  toggleModif() {
    this._modif = !this._modif && this.modif_allowed;
    this.eventEmitter.emit("parcours:modifEnabled", this._modif);
    return this._modif;
  }
  selectStand(id) {
    if (!this._modif) return;
    this.eventEmitter.emit("stand:selected", id);
  }
  selectSegment(id) {
    if (!this._modif) return;
    this.eventEmitter.emit("segment:selected", id);
  }
  segmentChange(id, trace) {
    if (!this._modif) return;
    let change = {
      op: "segment:modif",
      id,
      trace
    };
    this.addOp(change);
  }
  async commitOp(op) {
    if (linearChanges.includes(op.op)) {
      this.commitChanges.push(...this.changes);
      this.changes = [];
      this.commitChanges.push(op);
    } else {
      const index = this.changes.findIndex((change) => change.op == op.op && change.id == op.id);
      if (index != -1) {
        for (const [key, value] of Object.entries(op)) {
          if (value != void 0) {
            this.changes[index][key] = value;
          } else {
            delete this.changes[index][key];
          }
        }
      } else {
        this.changes.push(op);
      }
    }
  }
  addOp(op) {
    void this.commitOp(op);
    this.eventEmitter.emit(op.op, op);
  }
  static async fetch(event_id, parcours_id) {
    const url = `/api/v1/parcours/get_parcours/${event_id}/${parcours_id}`;
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(`Response status: ${response.status}`);
    }
    const result = await response.json();
    return _ParcoursData.fromJson(result);
  }
  static fromJson(data) {
    return new _ParcoursData(data.id, data.name, data.description, new Date(data.creation_date), data.stands.map((stand) => StandData.fromJson(stand)), data.segments.map((segment) => SegmentData.fromJson(segment)), data.modif, data.modif_allowed);
  }
  static empty() {
    return new _ParcoursData(0, "", "", /* @__PURE__ */ new Date(), [], [], false, false);
  }
};
var StandData = class _StandData {
  constructor(parcours, id, name, lat, lng, ele, color, chrono) {
    this.parcours = parcours;
    this.id = id;
    this.selected = false;
    this.eventEmitter = createNanoEvents();
    this._name = name;
    this._lat = lat;
    this._lng = lng;
    this._ele = ele;
    this._color = color;
    this._chrono = chrono;
    parcours.on("stand:selected", (id2) => {
      if (id2 == this.id && !this.selected) {
        this.eventEmitter.emit("selected", true);
        this.selected = true;
      } else if (id2 != this.id && this.selected) {
        this.eventEmitter.emit("selected", false);
        this.selected = false;
      }
    });
    parcours.on("segment:selected", (id2) => {
      if (this.selected) {
        this.selected = false;
        this.eventEmitter.emit("selected", false);
      }
    });
    parcours.on("parcours:modifEnabled", (enabled) => {
      if (!enabled) {
        this.selected = false;
        this.eventEmitter.emit("selected", false);
      }
    });
  }
  on(event, callback) {
    return this.eventEmitter.on(event, callback);
  }
  get name() {
    return this._name;
  }
  set name(value) {
    this._name = value;
  }
  get lat() {
    return this._lat;
  }
  get lng() {
    return this._lng;
  }
  setLatLng(lat, lng) {
    this._lat = lat;
    this._lng = lng;
  }
  get color() {
    return this._color;
  }
  set color(value) {
    this._color = value;
  }
  get ele() {
    return this._ele;
  }
  set ele(value) {
    this._ele = value;
  }
  get chrono() {
    return this._chrono;
  }
  set chrono(value) {
    this._chrono = value;
  }
  static fromJson(data) {
    return (parcours) => new _StandData(parcours, data.id, data.name, data.lat, data.lng, data.ele, data.color, data.chrono);
  }
};
var SegmentData = class _SegmentData {
  constructor(parcours, id, start, to, trace, index) {
    this.parcours = parcours;
    this.id = id;
    this.start = start;
    this.to = to;
    this.index = index;
    this.eventEmitter = createNanoEvents();
    this.selected = false;
    this._trace = trace;
    parcours.on("stand:selected", (id2) => {
      if (this.selected) {
        this.selected = false;
        this.eventEmitter.emit("selected", false);
      }
    });
    parcours.on("segment:selected", (id2) => {
      if (id2 == this.id && !this.selected) {
        this.eventEmitter.emit("selected", true);
        this.selected = true;
      } else if (id2 != this.id && this.selected) {
        this.eventEmitter.emit("selected", false);
        this.selected = false;
      }
    });
    parcours.on("parcours:modifEnabled", (enabled) => {
      if (!enabled) {
        this.selected = false;
        this.eventEmitter.emit("selected", false);
      }
    });
  }
  get trace() {
    return this._trace;
  }
  set trace(trace) {
    this._trace = trace.map((point) => [point[0], point[1], point[2] ?? null]);
    this.parcours.segmentChange(this.id, this._trace);
  }
  on(event, callback) {
    return this.eventEmitter.on(event, callback);
  }
  static fromJson(data) {
    return (parcours) => new _SegmentData(parcours, data.id, data.start, data.to, data.trace, data.index);
  }
};
export {
  ParcoursData,
  SegmentData,
  StandData
};
//# sourceMappingURL=/static/js/parcours_data.js.map
