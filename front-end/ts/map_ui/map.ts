import { LatLngBoundsExpression, LayerGroup, Control, MapOptions, map, layerGroup, tileLayer, control, LatLngBounds, Map } from "leaflet"
import { LitElement, css, unsafeCSS, html } from "lit"
import { customElement, property } from "lit/decorators.js"
import { createRef, ref } from "lit/directives/ref.js"
import type { ParcoursData } from "../parcours_data.js"
import { SegmentController } from "./segment.js"
import leafletCss from 'inline:../../node_modules/leaflet/dist/leaflet.css'
import leafletContextMenuCss from 'inline:../../node_modules/leaflet-contextmenu/dist/leaflet.contextmenu.css'
import leafletSidebarCss from 'inline:../../node_modules/leaflet-sidebar-v2/css/leaflet-sidebar.css'
import { EditionController } from "./edition.js"
import { MarkerController } from "./marker.js"
import { InfoBar } from "./ui.js"
import 'leaflet-sidebar-v2'
import 'leaflet-contextmenu'

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
  public standEdit!: HTMLElement;
  public segmentEdit!: HTMLElement;
  public info!: InfoBar;
  private mapDivRef = createRef<HTMLDivElement>()
  public edition!: EditionController;
  private _markerControllers: { [k: number]: MarkerController } = {}
  statusIcon: any
  get markerControllers() { return this._markerControllers }
  private _segmentControllers: { [k: number]: SegmentController } = {}
  get segmentControllers() { return this._segmentControllers }

  firstUpdated() {
    // Initialize the map
    const map_options: MapOptions = {
      contextmenu: true,
      zoom: 1,
      center: [0, 0]
    }

    this.map = map(this.mapDivRef.value!, map_options)
    this.map.on('click', (ev) => this.map.contextmenu.hide())
    this.map.on('drag', (ev) => this.map.contextmenu.hide());
    this.tmp_layer = layerGroup().addTo(this.map);
    this.data.on('idsUpdated', this.updateId.bind(this))


    // Add tile layer
    tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      crossOrigin: 'anonymous', // allows CORS requests
      attribution:
        '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    }).addTo(this.map);

    this.info = new InfoBar({ position: 'topright' })
    this.info.addTo(this.map)

    this.edition = new EditionController(this, this.data)

    this.createSidebar();
    this.reload()
    this.edition.load()
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
      button: (e) => this.edition.toggleModif()
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
      title: 'Edit Segment',
      position: 'top',
      disabled: true
    }
    this.sidebar.addPanel(segmentEditOptions);
    this.segmentEdit = this.shadowRoot?.querySelector('#segmentedit') as HTMLElement
    this.data.on('segment:selected', () => { this.sidebar.enablePanel('segmentedit'); this.sidebar.disablePanel('standedit'); this.sidebar.open('segmentedit') })

    // creating status
    const statusPannel: Control.PanelOptions = {
      id: 'status',
      tab: '<div id="status"><iconify-icon icon="mdi:map-marker-plus" width="24" height="24"></iconify-icon></div>',
      position: 'bottom',
      button: () => { this.edition.stopEditing() }
    }
    this.sidebar.addPanel(statusPannel)
    this.statusIcon = this.shadowRoot?.querySelector('#status>iconify-icon')
    this.edition.on('statusChanged', (status) => {
      this.statusIcon.icon = status === null ? 'mdi:map-marker-path' : 'mdi:map-marker-plus';
    })
    // config pannel
    var panelContent: Control.PanelOptions = {
      id: 'config',                     // UID, used to access the panel
      tab: '<iconify-icon inline icon="mdi:gear"></iconify-icon>',  // content can be passed as HTML string,
      pane: `<iconify-icon height="20px" inline icon="mdi:pen-off"></iconify-icon>`,        // DOM elements can be passed, too
      title: 'Config',              // an optional pane header
      position: 'bottom'                  // optional vertical alignment, defaults to 'top'
    };
    this.sidebar.addPanel(panelContent);

    // replace the normal icon to a custom one
    this.shadowRoot?.querySelectorAll('.leaflet-sidebar-close')?.forEach(
      close => { close.innerHTML = `<iconify-icon inline icon="mdi:chevron-left"></iconify-icon>` })
  }

  render() {
    return html`
        <div ${ref(this.mapDivRef)} id="map" style="height: ${this.height}; width: ${this.width}"></div>
    `
  }

  // custom
  reload() {
    this.map.invalidateSize()
    const boundPoints: [number, number][] = []

    this.data.stands.forEach(stand => {
      this._markerControllers[stand.id] = new MarkerController(this, stand);
      boundPoints.push([stand.lat, stand.lng]);
    });

    this.data.segments.forEach(segment => {
      boundPoints.push(...segment.trace.map(c => [c[0], c[1]] as [number, number]))
      this._segmentControllers[segment.id] = new SegmentController(this, segment);
    });


    //if (this.bound != null || boundPoints.length > 0) {
    //  this.map.fitBounds(this.bound ?? (new LatLngBounds(boundPoints)));
    //}
  }
  private updateId(ids: Record<number, number>) {
    this._markerControllers = Object.keys(this._markerControllers).reduce((acc, key) => {
      // Use the new key if it exists in the map, otherwise keep the old key
      const newKey = ids[key as any as number] || key as any as number;
      acc[newKey] = this._markerControllers[key as any as number];
      return acc;
    }, {} as Record<number, any>);
    this._segmentControllers = Object.keys(this._segmentControllers).reduce((acc, key) => {
      // Use the new key if it exists in the map, otherwise keep the old key
      const newKey = ids[key as any as number] || key as any as number;
      acc[newKey] = this._segmentControllers[key as any as number];
      return acc;
    }, {} as Record<number, any>);
  }

  getMarkerController(id: number) {
    if (id in this.markerControllers) {
      return this.markerControllers[id]
    }
    return
  }
  getSegmentController(id: number) {
    if (id in this.segmentControllers) {
      return this.segmentControllers[id]
    }
    return
  }
}