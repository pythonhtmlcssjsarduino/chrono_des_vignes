import { Marker, marker, LatLng, divIcon } from "leaflet";
import { StandData } from "../parcours_data.js";
import { ParcoursMap } from "./map.js";
import 'iconify-icon'

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

export class MarkerController {
  public marker: Marker;
  readonly color: string = '#338888'
  readonly selectedColor: string = 'red'
  constructor(private map: ParcoursMap, public data: StandData) {
    this.marker = marker([data.lat, data.lng], {
      draggable: true,
      icon: markerIcon({ color: this.color }),
      contextmenu: true,
      contextmenuItems: [
        {
          text: 'get latlng', callback(ev, map) {
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
    data.on('latlngChanged', (lat, lng) => {
      this.marker.setLatLng([lat, lng])
    })
    data.on('selected', (selected) => {
      if (selected) {
        this.map.edition.modifyStand(data)
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