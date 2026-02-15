import { LeafletMouseEvent } from "leaflet";
import { html, render } from "lit";
import { createRef, ref } from "lit/directives/ref.js";
import { Field, LitForm } from "../forms.js";
import { ParcoursData, SegmentData, StandData } from "../parcours_data.js";
import { ParcoursMap } from "./map.js";
import { MarkerController } from "./marker.js";
import { SegmentController } from "./segment.js";
import '../forms.js'
import { createNanoEvents } from "nanoevents";


function round(num: number, n: number) {
  return Math.round(num * Math.pow(10, n)) / Math.pow(10, n)
}

interface EditionEvent {
  statusChanged: (status: 'stand' | 'segment' | null) => void
}

export class EditionController {
  private last_point?: MarkerController
  private extended_segment?: SegmentController
  private creating_first_marker: boolean = false
  private stand_form!: StandForm
  private eventEmitter = createNanoEvents<EditionEvent>()

  constructor(private map: ParcoursMap, private data: ParcoursData) {
    this.map.map.on('click', this.click.bind(this))
    if (this.data.isEmpty()) {
      console.log('empty parcours creating a new one');
      this.creating_first_marker = true
      this.map.info.setText('click on the map to add the first ')
    }

  }

  load() {
    //forms
    this.stand_form = new StandForm(this.map.standEdit)
  }

  on<E extends keyof EditionEvent>(event: E, callback: EditionEvent[E]) {
    return this.eventEmitter.on(event, callback)
  }

  enableModif() { this.data.enableModif() }
  disableModif() { this.data.disableModif() }
  toggleModif() { this.data.toggleModif() }

  continuePolyline(polyline: SegmentController) {
    throw new Error("not implemented");

  }
  extendFromStand(stand: MarkerController) {
    throw new Error("not implemented");

  }
  stopEditing() {
    console.log(this.last_point, this.extended_segment);

    if (this.last_point || this.extended_segment) {
      delete this.last_point
      delete this.extended_segment
      this.eventEmitter.emit('statusChanged', null)
    }
  }

  click(event: LeafletMouseEvent) {
    if (!this.data.modif) return
    if (this.creating_first_marker) {
      const controller = MarkerController.create(this.map, event.latlng)
      this.creating_first_marker = false
      this.map.info.clear()
      this.last_point = controller
      this.map.markerControllers[controller.data.id] = controller
    } else if (this.last_point && !this.extended_segment) {
      console.log('click');
      const stand = MarkerController.create(this.map, event.latlng)
      this.map.markerControllers[stand.data.id] = stand
      const segment = SegmentController.create(this.map, this.last_point, stand, 0)
      delete this.last_point
      this.extended_segment = segment
      this.map.segmentControllers[segment.data.id] = segment
    } else if (!this.last_point && this.extended_segment) {
      console.log('extending');
      const trace = [...this.extended_segment.data.trace, [this.extended_segment.end.data.lat, this.extended_segment.end.data.lng] as [number, number]]
      this.extended_segment.end.data.setLatLng(event.latlng.lat, event.latlng.lng)
      this.extended_segment.data.trace = trace
    }
  }

  modifySegment(segment: SegmentData) {
    const fields: Field[] = []
    const panel = html`
      <lit-form .fields=${fields}></lit-form>
    `

    render(panel, this.map.segmentEdit)
  }

  modifyStand(stand: StandData) {
    this.stand_form.editStand(stand)
  }
}

class StandForm {
  private current_stand?: StandData
  private form_ref = createRef<LitForm>()
  private callback_list: Function[] = []
  constructor(div: HTMLElement) {
    const fields: Field[] = [
      {
        type: 'string', name: 'name', label: 'nom', value: '', required: true, updater: (value) => {
          if (this.current_stand) {
            this.current_stand.name = value
          }
        },
      },
      {
        type: 'boolean', name: 'chrono', label: 'chrono', value: false, updater: (value) => {
          if (this.current_stand) {
            this.current_stand.chrono = value
          }
        }
      },
      {
        type: 'group', name: 'latlng', label: 'position', fields: [
          {
            type: 'number', name: 'lat', label: 'latitude', value: 0, precision: 7, required: true, updater: (value) => {
              if (this.current_stand) {
                this.current_stand.lat = value
              }
            },
          },
          {
            type: 'number', name: 'lng', label: 'longitude', value: 0, precision: 7, required: true, updater: (value) => {
              if (this.current_stand) {
                this.current_stand.lng = value
              }
            },
          }
        ]
      },
    ]

    const panel = html`
      <lit-form ${ref(this.form_ref)} .fields=${fields} ?noSubmit=${true}></lit-form>
    `

    render(panel, div)
  }

  editStand(stand: StandData) {
    console.warn('mod stand', stand);
    this.callback_list.forEach((c) => c())

    this.current_stand = stand
    this.form_ref.value?.setString('name', stand.name)
    this.form_ref.value?.setNumber('lat', round(stand.lat, 6))
    this.form_ref.value?.setNumber('lng', round(stand.lng, 6))
    this.form_ref.value?.setBoolean('chrono', stand.chrono)

    this.callback_list = [
      stand.on('nameChanged', (name) => {
        this.form_ref.value?.setString('name', name)
      }),
      stand.on('latlngChanged', (lat, lng) => {
        this.form_ref.value?.setNumber('lat', round(lat, 6))
        this.form_ref.value?.setNumber('lng', round(lng, 6))
      }),
      stand.on('chronoChanged', (chrono) => {
        this.form_ref.value?.setBoolean('chrono', chrono)
      })
    ]
  }
}