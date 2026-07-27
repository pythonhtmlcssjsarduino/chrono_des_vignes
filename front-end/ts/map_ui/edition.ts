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
  private extendedSegment?: SegmentController
  private creatingFirstMarker: boolean = false
  private stand_form!: StandForm
  private eventEmitter = createNanoEvents<EditionEvent>()

  constructor(private map: ParcoursMap, private data: ParcoursData) {
  }

  load() {
    this.map.map.on('click', this.click.bind(this))
    if (this.data.isEmpty()) {
      console.log('empty parcours creating a new one');
      this.creatingFirstMarker = true
      this.map.info.setText('click on the map to add the first ')
    } else {
      const stand = this.map.getMarkerController(this.data.get_last_stand()!.id)!
      stand.contextMenu.addItem({
        id: 'extend', text: 'new step from hier', callback: () => {
          this.extendFromStand(stand)
        }
      })

      const segment = this.data.get_last_segment()
      if (segment) {
        stand.contextMenu.addItem({
          id: 'continue', text: 'continue from hier', callback: () => {
            this.continuePolyline(this.map.getSegmentController(segment.id)!)
          }
        })
        this.eventEmitter.emit('statusChanged', null)
      } else {
        this.extendFromStand(stand)
      }
    }
    this.data.on('stand:selected', (id) => {
      const stand = this.data.get_stand(id)
      if (stand && this.extendedSegment && this.extendedSegment.data.to != id) {

        const trace = [...this.extendedSegment.data.trace, this.extendedSegment.end.data.latlng]
        const toDel = this.extendedSegment.data.to
        this.extendedSegment.data.updateEnd(stand.id)
        const controller = this.map.getMarkerController(stand.id)!
        this.extendedSegment.end = controller
        this.extendedSegment.data.trace = trace
        this.data.deleteStand(toDel)
        this.extendFromStand(controller)
      }
    })
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
    if (this.data.get_last_segment() != polyline.data) {
      return
    }
    if (this.last_point || this.extendedSegment != polyline) {
      this.extendedSegment = polyline
      delete this.last_point
      this.eventEmitter.emit('statusChanged', 'segment')
      this.map.info.setText('click on the map to continue the polyline')
    }
  }
  extendFromStand(stand: MarkerController) {
    if (this.data.get_last_stand() != stand.data) {
      return
    }
    if (this.last_point != stand || this.extendedSegment) {
      this.last_point = stand
      delete this.extendedSegment
      this.eventEmitter.emit('statusChanged', 'stand')
      this.map.info.setText('click on the map to add a step after ' + stand.data.name)
    }
  }
  stopEditing() {
    if (this.last_point || this.extendedSegment) {
      if (this.last_point) {
        this.last_point.contextMenu.removeItem('extend')
      }
      delete this.last_point
      delete this.extendedSegment

      const last = this.map.getMarkerController(this.data.get_last_stand()!.id)
      if (last) {
        last.contextMenu.addItem({
          id: 'extend', text: 'new step from hier', callback: () => {
            this.extendFromStand(last)
          }
        })
      }
      this.map.info.clear()
      this.eventEmitter.emit('statusChanged', null)
    }
  }

  click(event: LeafletMouseEvent) {
    if (!this.data.modif) return
    if (this.creatingFirstMarker) {
      const controller = MarkerController.create(this.map, event.latlng)

      controller.contextMenu.addItem({
        id: 'extend', text: 'new step from hier', callback: () => {
          this.extendFromStand(controller)
        }
      })

      this.creatingFirstMarker = false
      this.map.info.clear()
      this.last_point = controller
      this.map.markerControllers[controller.data.id] = controller
    } else if (this.last_point && !this.extendedSegment) {
      console.log('click');
      const stand = MarkerController.create(this.map, event.latlng)
      this.last_point?.contextMenu.removeItem('extend')
      this.last_point?.contextMenu.removeItem('continue')

      this.map.markerControllers[stand.data.id] = stand
      let index = (this.data.get_last_segment()?.index ?? -1) + 1
      const segment = SegmentController.create(this.map, this.last_point, stand, index)

      stand.contextMenu.addItem({
        id: 'extend', text: 'new step from hier', callback: () => {
          this.extendFromStand(stand)
        }
      })
      stand.contextMenu.addItem({
        id: 'continue', text: 'continue from hier', callback: () => {
          this.continuePolyline(segment)
        }
      })

      delete this.last_point
      this.extendedSegment = segment
      this.map.segmentControllers[segment.data.id] = segment
    } else if (!this.last_point && this.extendedSegment) {
      console.log('extending');
      const trace = [...this.extendedSegment.data.trace, [this.extendedSegment.end.data.lat, this.extendedSegment.end.data.lng] as [number, number]]
      this.extendedSegment.end.data.setLatLng(event.latlng.lat, event.latlng.lng)
      this.extendedSegment.data.trace = trace
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