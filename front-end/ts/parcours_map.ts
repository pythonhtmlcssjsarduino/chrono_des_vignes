import { map, Map, tileLayer, marker, polyline, Icon, LatLngBounds, LatLngBoundsExpression, Polyline, Marker, LayerGroup, layerGroup, control, LatLng, Draggable, divIcon, LatLngExpression, Control, icon, LeafletEvent, DomUtil, MapOptions, LeafletMouseEvent, latLng as leafletLatlng, latLng } from 'leaflet';
import { LitElement, html, css, TemplateResult, render, unsafeCSS } from 'lit';
import { customElement, property } from 'lit/decorators.js';
import { ParcoursData, stand, segment, StandData, SegmentData } from './parcours_data';
import leafletCss from 'inline:../node_modules/leaflet/dist/leaflet.css'
import 'leaflet-contextmenu'
import leafletContextMenuCss from 'inline:../node_modules/leaflet-contextmenu/dist/leaflet.contextmenu.css'
import 'leaflet-sidebar-v2'
import leafletSidebarCss from 'inline:../node_modules/leaflet-sidebar-v2/css/leaflet-sidebar.css'
import 'iconify-icon'
import './forms'
import { Field, LitForm } from './forms';
import formCss from 'inline:../node_modules/nice-forms.css/dist/nice-forms.css'
import { createRef, ref } from 'lit/directives/ref.js';
/**
  // @ts-ignore
  import iconUrl from "leaflet/dist/images/marker-icon.png";
  // @ts-ignore
  import iconRetinaUrl from "leaflet/dist/images/marker-icon-2x.png";
  // @ts-ignore
  import shadowUrl from "leaflet/dist/images/marker-shadow.png";

  (Icon.Default as any).mergeOptions({
    iconUrl,
    iconRetinaUrl,
    shadowUrl
  });
 */
function translate(text: string) { return text }
interface markerIconConfig {
  icon?: iconName
  iconSize?: [number, number],
  iconAnchor?: [number, number],
  color?: string,
}
type iconName =
  | 'account'
  | 'alert'
  | 'check'
  | 'down'
  | 'left'
  | 'minus'
  | 'multible'
  | 'off'
  | 'plus'
  | 'question'
  | 'radius'
  | 'remove'
  | 'remove-variant'
  | 'right'
  | 'start'
  | 'up'

function markerIcon(config: markerIconConfig) {
  const iconSize = config.iconSize ?? [37, 61]
  const iconAnchor = config.iconAnchor ?? [19 / 37 * iconSize[0], 46 / 61 * iconSize[1]]
  const color = config.color ?? '#000'
  return divIcon({
    className: "iconify-marker",
    html: `<iconify-icon noobserver icon="mdi:map-marker${config.icon ? '-' + config.icon : ''}", width="${iconSize[0]}", height="${iconSize[1]}" style="color:${color}"></iconify-icon>`,
    iconAnchor: iconAnchor,
  })
}

@customElement('parcours-map')
export class ParcoursMap extends LitElement {
  static styles = [
    css`
      :host {
        display: block;
      }
      .vertex-handle {
        width: 12px;
        height: 12px;
        border-radius: 50%;         /* circle shape */
        border: 2px solid #3388ff;  /* border color and width */
        background-color: white;    /* fill color */
        cursor: move;
        box-sizing: border-box;
      }

      .middle{
        opacity: 0.5;
      }
    `,
    unsafeCSS(leafletCss),
    unsafeCSS(leafletContextMenuCss),
    unsafeCSS(leafletSidebarCss),
    unsafeCSS(formCss),
    css`.info-bar {
      background: white;
      padding: 6px 12px;
      border-radius: 5px;
      box-shadow: 0 0 5px rgba(0,0,0,0.3);
      font-family: sans-serif;
      font-size: 14px;
    }`
  ];

  @property({ attribute: false }) data!: ParcoursData
  @property({ attribute: false }) bound: LatLngBoundsExpression | null = null
  @property() height: string = '400px'
  @property() width: string = '400px'

  public map!: Map;
  public tmp_layer!: LayerGroup
  private sidebar!: Control.Sidebar;
  private modifIcon: any;
  private standEdit!: HTMLElement;
  private segmentEdit!: HTMLElement;
  public info!: InfoBar;
  private mapDivRef = createRef<HTMLDivElement>()

  firstUpdated() {
    // Initialize the map
    const map_options: MapOptions = {
      contextmenu: true
    }

    this.map = map(this.mapDivRef.value!, map_options)
    this.map.on('click', (ev) => this.map.contextmenu.hide())
    this.map.on('drag', (ev) => this.map.contextmenu.hide());
    this.tmp_layer = layerGroup().addTo(this.map);

    this.createSidebar();

    // Add tile layer
    tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      crossOrigin: 'anonymous', // allows CORS requests
      attribution:
        '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    }).addTo(this.map);

    this.info = new InfoBar({ position: 'topright' })
    this.info.addTo(this.map)

    this.reload()
  }

  createSidebar() {
    this.sidebar = control.sidebar({
      autopan: true,
      closeButton: true,
    }).addTo(this.map);

    /* add a new panel */
    var panelContent: Control.PanelOptions = {
      id: 'modif',                     // UID, used to access the panel
      tab: `<div id="modif"><iconify-icon inline icon="mdi:pen-off"></iconify-icon><div>`,  // content can be passed as HTML string,
      title: 'Modif',              // an optional pane header
      position: 'top',                  // optional vertical alignment, defaults to 'top'
      button: (e) => this.toggleModif()
    };
    this.sidebar.addPanel(panelContent);
    this.modifIcon = this.shadowRoot?.querySelector('#modif>iconify-icon')
    this.data.on('parcours:modifEnabled', (enabled) => {
      this.modifIcon.icon = enabled ? 'mdi:pen-off' : 'mdi:pen';
      enabled ? this.tmp_layer.addTo(this.map) : this.tmp_layer.remove()
      if (!enabled) {
        this.sidebar.close()
        this.sidebar.disablePanel('standedit');
        this.sidebar.disablePanel('segmentedit');
      }
    })

    // stand modif pannel
    const standEditOptions: Control.PanelOptions = {
      id: 'standedit',
      tab: '<iconify-icon height="30px" inline icon="mdi:vector-point-edit"></iconify-icon>',
      pane: '<div id="standedit"></div>',
      title: 'Edit Stand',
      position: 'top',
      disabled: true
    };
    this.sidebar.addPanel(standEditOptions);
    this.standEdit = this.shadowRoot?.querySelector('#standedit') as HTMLElement
    this.data.on('stand:selected', () => { this.sidebar.enablePanel('standedit'); this.sidebar.disablePanel('segmentedit'); this.sidebar.open('standedit') })

    const segmentEditOptions: Control.PanelOptions = {
      id: 'segmentedit',
      tab: '<iconify-icon height="30px" inline icon="mdi:vector-polyline-edit"></iconify-icon>',
      pane: '<div id="segmentedit"></div>',
      title: 'Edit Stand',
      position: 'top',
      disabled: true
    }
    this.sidebar.addPanel(segmentEditOptions);
    this.segmentEdit = this.shadowRoot?.querySelector('#segmentedit') as HTMLElement
    this.data.on('segment:selected', () => { this.sidebar.enablePanel('segmentedit'); this.sidebar.disablePanel('standedit'); this.sidebar.open('segmentedit') })

    var panelContent: Control.PanelOptions = {
      id: 'config',                     // UID, used to access the panel
      tab: '<iconify-icon inline icon="mdi:gear"></iconify-icon>',  // content can be passed as HTML string,
      pane: `<iconify-icon height="20px" inline icon="mdi:pen-off"></iconify-icon>`,        // DOM elements can be passed, too
      title: 'Config',              // an optional pane header
      position: 'bottom'                  // optional vertical alignment, defaults to 'top'
    };
    this.sidebar.addPanel(panelContent);

    this.shadowRoot?.querySelectorAll('.leaflet-sidebar-close')?.forEach(
      close => { close.innerHTML = `<iconify-icon inline icon="mdi:chevron-left"></iconify-icon>` })
  }

  modifySegment(segment: SegmentData) {
    const fields: Field[] = []
    const panel = html`
      <lit-form .fields=${fields}></lit-form>
    `

    render(panel, this.segmentEdit)
  }

  modifyStand(stand: StandData) {
    const form_ref = createRef<LitForm>()
    const fields: Field[] = [
      {
        type: 'string', name: 'name', label: 'nom', value: stand.name, required: true, updater(value) {
          stand.name = value
        },
      },
      {
        type: 'boolean', name: 'chrono', label: 'chrono', value: stand.chrono, updater(value) {
          stand.chrono = value
        }
      },

      {
        type: 'group', name: 'latlng', label: 'position', fields: [
          {
            type: 'number', name: 'lat', label: 'latitude', value: stand.lat, precision: 7, required: true, updater(value) {
              stand.lat = value
            },
          },
          {
            type: 'number', name: 'lng', label: 'longitude', value: stand.lng, precision: 7, required: true, updater(value) {
              stand.lng = value
            },
          }
        ]
      },
    ]

    stand.on('nameChanged', (name) => {
      form_ref.value!.setString('name', name)
    })
    stand.on('latlngChanged', (lat, lng) => {
      form_ref.value!.setNumber('lat', lat)
      form_ref.value!.setNumber('lng', lng)
    })
    stand.on('chronoChanged', (chrono) => {
      form_ref.value!.setBoolean('chrono', chrono)
    })

    const panel = html`
      <lit-form ${ref(form_ref)} .fields=${fields} ?noSubmit=${true}></lit-form>
    `

    render(panel, this.standEdit)
  }

  render() {
    return html`
        <div ${ref(this.mapDivRef)} id="map" style="height: ${this.height}; width: ${this.width}"></div>
    `
  }

  enableModif() { this.data.enableModif() }
  disableModif() { this.data.disableModif() }
  toggleModif() { this.data.toggleModif() }

  // custom
  reload() {
    this.map.invalidateSize()
    const boundPoints: [number, number][] = []

    let markers: { [key: number]: MarkerController } = {};
    this.data.stands.forEach(stand => {
      markers[stand.id] = new MarkerController(this, stand);
      boundPoints.push([stand.lat, stand.lng]);
    });

    this.data.segments.forEach(segment => {
      boundPoints.push(...segment.trace.map(c => [c[0], c[1]] as [number, number]))
      new SegmentController(this, segment, markers);
    });

    if (this.bound != null || boundPoints.length > 0) {
      this.map.fitBounds(this.bound ?? (new LatLngBounds(boundPoints)));
    } else {
      this.map.fitWorld()
      this.map.setZoom(1)
    }

    new EditionController(this, this.data)
  }
}

class EditionController {
  private last_point?: MarkerController
  private extended_segment?: SegmentController
  private creating_first_marker: boolean = false

  constructor(private map: ParcoursMap, private data: ParcoursData) {
    this.map.map.addEventListener('click', this.click.bind(this))
    if (this.data.isEmpty()) {
      console.log('empty');
      this.creating_first_marker = true
      this.map.info.setText(translate('click on the map to add the first '))

    }
  }

  click(event: LeafletMouseEvent) {
    if (this.creating_first_marker) {
      MarkerController.create(this.map, event.latlng)
      this.creating_first_marker = false
    }
  }
}

class MarkerController {
  public marker: Marker;
  readonly color: string = '#338888'
  readonly selectedColor: string = 'red'
  constructor(private map: ParcoursMap, data: StandData) {
    this.marker = marker([data.lat, data.lng], {
      draggable: true,
      icon: markerIcon({ color: this.color }),
      contextmenu: true,
      contextmenuItems: [
        {
          text: translate('get latlng'), callback(ev, map) {
            console.log((ev.relatedTarget as any).getLatLng());
          }
        },
      ]
    }
    ).addTo(this.map.map);
    this.marker.on('click', (e) => {
      this.map.data.selectStand(data.id);
    })
    this.marker.on('drag', (e) => {
      const markerlatlng = this.marker.getLatLng()
      data.setLatLng(markerlatlng.lat, markerlatlng.lng)
    })
    data.on('selected', (selected) => {
      if (selected) {
        this.map.modifyStand(data)
        this.marker.setIcon(markerIcon({ color: this.selectedColor }))
      } else {
        this.marker.setIcon(markerIcon({ color: this.color }))
      }
    })
    this.map.data.on('parcours:modifEnabled', (enabled) => enabled ? this.marker.dragging?.enable() : this.marker.dragging?.disable())
  }

  static create(map: ParcoursMap, latlng: LatLng,/** name?: string, ele?: number | null, color?: string, */ chrono?: boolean) {
    console.log('stand created')
    const stand = map.data.createStand(latlng.lat, latlng.lng, chrono ?? false)
    const controller = new MarkerController(map, stand)
    map.data.selectStand(stand.id);
    return controller
  }
}

class SegmentController {
  public polyline: Polyline;
  private vertexs: Marker[] = [];
  start: MarkerController
  end: MarkerController
  readonly color: string = '#3388ff'
  readonly selectedColor: string = 'red'

  constructor(private map: ParcoursMap, private data: SegmentData, markers: { [key: number]: MarkerController }) {
    if (data.id == 109) {
      // log start stand , points and end stand latlng
      console.log(data.id)
      console.log(markers[data.start].marker.getLatLng().toString())
      console.log(data.trace.map(c => `LatLng(${c[0].toFixed(4)}, ${c[1].toFixed(4)})`).join(', '))
      console.log(markers[data.to].marker.getLatLng().toString())
    }
    const polyPoints: [number, number][] = []
    const start = this.map.data.get_stand(data.start)!;
    this.start = markers[start.id]
    polyPoints.push([start.lat, start.lng]);
    polyPoints.push(...data.trace.map(c => [c[0], c[1]] as [number, number]));
    const end = this.map.data.get_stand(data.to)!;
    this.end = markers[end.id]
    polyPoints.push([end.lat, end.lng]);
    this.polyline = polyline(polyPoints, { color: this.color }).addTo(this.map.map);

    data.on('selected', (selected) => {
      if (selected) {
        this.map.modifySegment(data)
        this.polyline.setStyle({ color: this.selectedColor })
      } else {
        this.polyline.setStyle({ color: this.color })
      }
    })

    // link marker and polyline
    this.vertexs = []

    this.start.marker.on('drag', (e) => {
      const points = this.polyline.getLatLngs() as LatLng[];
      points[0] = this.start.marker.getLatLng();

      this.polyline.setLatLngs(points);
      this.vertexs[0].setLatLng(this.mapMiddle(points[0], points[1]));
    })

    this.end.marker.on('drag', (e) => {
      const points = this.polyline.getLatLngs() as LatLng[];
      points[points.length - 1] = this.end.marker.getLatLng();

      this.polyline.setLatLngs(points);
      this.vertexs[this.vertexs.length - 1].setLatLng(this.mapMiddle(points[points.length - 2], points[points.length - 1]));
    })

    this.polyline.on('click', () => { this.map.data.selectSegment(data.id) })

    const c = marker(this.mapMiddle(polyPoints[0], polyPoints[1]), {
      draggable: true,
      icon: divIcon({
        className: "vertex-handle middle",
      }),
      contextmenu: false,
      contextmenuItems: []
    }).addTo(this.map.tmp_layer);

    c.on('drag', (e) => {
      this.addMiddlePoint(this.vertexs.indexOf(c));
      this.commitOp();
    })
    this.vertexs.push(c)

    polyPoints.slice(1, -1).forEach((latlng, i, arr) => {
      if (data.id == 109) {
        // log latlng
        console.log(`vertex #${i} LatLng(${latlng[0].toFixed(4)}, ${latlng[1].toFixed(4)})`)

        console.log(latlng, arr[i + 1] ?? polyPoints[polyPoints.length - 1], this.mapMiddle(latlng, arr[i + 1] ?? polyPoints[polyPoints.length - 1]));

      }
      //main
      this.vertexs.push(this.makeVertexHandele(latlng))

      // middle
      this.vertexs.push(this.makeMiddleVertexHandle(latlng, arr[i + 1] ?? polyPoints[polyPoints.length - 1]))
    })
  }
  commitOp() {
    this.data.trace = (this.polyline.getLatLngs() as LatLng[]).map((latlng) => [latlng.lat, latlng.lng])
  }
  mapMiddle(a: LatLngExpression, b: LatLngExpression) {
    console.log(`mapmiddle (${a}), (${b}) -> ${this.map.map.layerPointToLatLng(this.map.map.latLngToLayerPoint(a).add(this.map.map.latLngToLayerPoint(b)).divideBy(2))}`);

    return this.map.map.layerPointToLatLng(this.map.map.latLngToLayerPoint(a).add(this.map.map.latLngToLayerPoint(b)).divideBy(2));
  }
  refreshMiddleVertex(index: number) {
    const a = this.vertexs[index - 1]?.getLatLng() ?? this.start.marker.getLatLng();
    const b = this.vertexs[index + 1]?.getLatLng() ?? this.end.marker.getLatLng();

    this.vertexs[index].setLatLng(this.mapMiddle(a, b))
  }
  addMiddlePoint(index: number) {
    const selected = this.vertexs[index];
    selected.once('dragend', (e) => {
      selected.setIcon(divIcon({
        className: "vertex-handle",
      }))
    })
    console.log(selected);

    selected.bindContextMenu({
      contextmenu: true, contextmenuItems: [{
        text: 'test', callback(ev, map) {
          console.log((ev.relatedTarget as any).getLatLng());
        }
      }]
    });
    selected.off('drag')
    selected.on('drag', (e) => {
      const points = this.polyline.getLatLngs() as LatLng[];
      const index = this.vertexs.indexOf(selected);
      points.splice(index / 2 + 1, 1, selected.getLatLng());
      this.polyline.setLatLngs(points);
      this.refreshMiddleVertex(index - 1);
      this.refreshMiddleVertex(index + 1);
    })
    selected.on('dblclick', (e) => {
      this.deletePoint(this.vertexs.indexOf(selected));
      this.commitOp();
    })

    const points = this.polyline.getLatLngs() as LatLng[];
    points.splice(index / 2 + 1, 0, selected.getLatLng());
    this.polyline.setLatLngs(points);

    const last = this.vertexs[index - 1] ?? this.start.marker
    const next = this.vertexs[index + 1] ?? this.end.marker
    //this.vertexs.splice(index+1, 0, 'hello')
    //this.vertexs.splice(index, 0, 'hello')
    const newm = this.makeMiddleVertexHandle(last.getLatLng(), selected.getLatLng())
    this.vertexs.splice(index + 1, 0, newm)

    const newp = this.makeMiddleVertexHandle(selected.getLatLng(), next.getLatLng())
    this.vertexs.splice(index, 0, newp)
  }
  deletePoint(index: number) {
    const points = this.polyline.getLatLngs() as LatLng[];
    const selected = this.vertexs[index];
    selected.setIcon(divIcon({
      className: "vertex-handle middle",
    }))
    selected.off('drag')
    selected.off('dblclick')
    selected.on('drag', (e) => {
      this.addMiddlePoint(this.vertexs.indexOf(selected));
      this.commitOp();
    })

    this.map.tmp_layer.removeLayer(this.vertexs.splice(index + 1, 1)[0]);
    this.map.tmp_layer.removeLayer(this.vertexs.splice(index - 1, 1)[0]);
    points.splice((index + 1) / 2, 1);
    this.polyline.setLatLngs(points);
    this.refreshMiddleVertex(index - 1);
    return
  }
  makeVertexHandele(latlng: LatLngExpression) {
    const c = marker(latlng, {
      draggable: true,
      icon: divIcon({
        className: "vertex-handle",
      }),
      contextmenu: true,
      contextmenuItems: [
        {
          text: 'make a Stand', callback(ev, map) {
            console.log(ev, map);
          },
        },
        {
          text: 'get latlng', callback(ev, map) {
            console.log(c.getLatLng());
          },
        }
      ]
    }).addTo(this.map.tmp_layer);

    c.on('dblclick', (e) => {
      this.deletePoint(this.vertexs.indexOf(c));
      this.commitOp();
    })
    c.on('drag', (e) => {
      const points = this.polyline.getLatLngs() as LatLng[];
      const index = this.vertexs.indexOf(c);
      points.splice(index / 2 + 1, 1, c.getLatLng());
      this.polyline.setLatLngs(points);
      this.refreshMiddleVertex(index - 1);
      this.refreshMiddleVertex(index + 1);
      this.commitOp();
    })
    return c
  }
  makeMiddleVertexHandle(a: LatLngExpression, b: LatLngExpression) {
    const cm = marker(this.mapMiddle(a, b), {
      draggable: true,
      icon: divIcon({
        className: "vertex-handle middle",
      }),
      contextmenu: true,
      contextmenuItems: [
        {
          text: 'get latlng', callback(ev, map) {
            console.log(cm.getLatLng());
          },
        }
      ]
    }).addTo(this.map.tmp_layer);
    cm.on('drag', (e) => {
      this.addMiddlePoint(this.vertexs.indexOf(cm));
      this.commitOp();
    })
    return cm
  }
}

class InfoBar extends Control {
  private _div: HTMLDivElement | undefined;

  constructor(opts?: L.ControlOptions) {
    super(opts);
  }

  onAdd(map: L.Map): HTMLElement {
    this._div = DomUtil.create('div', 'info-bar');
    this._div.innerText = '';
    this._div.hidden = true;
    return this._div;
  }

  setText(text: string) {
    if (this._div) {
      this._div.innerText = text
      this._div.hidden = false
    };
  }

  clear() {
    if (this._div) {
      this._div.hidden = true
    }
  }
}


declare global {
  interface HTMLElementTagNameMap {
    "parcours-map": ParcoursMap
  }
}