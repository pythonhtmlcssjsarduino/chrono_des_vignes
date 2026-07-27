import { Polyline, LayerGroup, polyline, LatLngExpression, marker, divIcon, Marker } from "leaflet";
import { SegmentData } from "../parcours_data.js";
import { ParcoursMap } from "./map.js";
import { MarkerController } from "./marker.js";


export class SegmentController {
  public polyline: Polyline;
  private tmp_layer: LayerGroup
  private vertexs: VertexMarker[] = [];
  private edges: EdgeMarker[] = [];
  start: MarkerController
  end: MarkerController
  readonly color: string = '#3388de'
  readonly selectedColor: string = 'red'
  public dragging?: 'vertex' | 'edge'

  constructor(private map: ParcoursMap, public data: SegmentData) {
    this.tmp_layer = this.map.tmp_layer
    const start = this.map.data.get_stand(data.start)!;
    this.start = map.markerControllers[start.id]
    const end = this.map.data.get_stand(data.to)!;
    this.end = map.markerControllers[end.id]
    const polyPoints = [[start.lat, start.lng], ...data.trace.map(c => [c[0], c[1]]), [end.lat, end.lng]] as [number, number][]
    this.polyline = polyline(polyPoints, { color: this.color }).addTo(this.map.map);

    data.on('selected', (selected) => {
      if (selected) {
        this.map.edition.modifySegment(data)
        this.polyline.setStyle({ color: this.selectedColor })
      } else {
        this.polyline.setStyle({ color: this.color })
      }
    })
    data.on('traceChanged', (trace) => {
      if (!this.dragging) {
        this.updateMarkers()
      } else {
        this.updatePolyline()
        if (this.dragging == 'edge') {
          this.updateVertexs()
        } else if (this.dragging = 'vertex') {
          this.updateEdges()
        }
      }
    })
    this.polyline.on('click', (e) => {
      data.select()
    })

    start.on('latlngChanged', (lat, lng) => {
      this.updateMarkers()
    })
    end.on('latlngChanged', (lat, lng) => {
      this.updateMarkers()
    })
    this.updateMarkers()
  }

  modifyVertex(index: number, lat: number, lng: number) {
    this.data.setTracePoint(index, [lat, lng])
  }

  removeVertex(index: number) {
    const trace = this.data.trace
    trace.splice(index, 1)
    this.data.trace = trace
  }

  addVertex(fromIndex: number, lat: number, lng: number) {
    const trace = this.data.trace
    this.data.trace = [...trace.slice(0, fromIndex), [lat, lng], ...trace.splice(fromIndex)]
  }

  private updatePolyline() {
    const polypoints = [this.start.data.latlng, ...(this.data.trace.map((point) => [point[0], point[1]] as [number, number])), this.end.data.latlng]
    this.polyline.setLatLngs(polypoints)
  }

  updateMarkers() {
    this.updatePolyline()
    this.updateEdges()
    this.updateVertexs()
  }

  private updateVertexs() {
    var vertexs = this.vertexs
    this.vertexs = []
    this.data.trace.forEach(([lat, lng], index) => {
      let vertex = vertexs.pop();
      if (!vertex) {
        vertex = new VertexMarker(this, this.tmp_layer)
      }
      vertex.update(index, lat, lng)
      this.vertexs.push(vertex)
    })
    vertexs.forEach((vertex) => vertex.delete())
  }

  private updateEdges() {
    var edges = this.edges
    this.edges = []
    let arra = [this.start.data.latlng, ...this.data.trace]
    let arrb = [...this.data.trace, this.end.data.latlng]
    for (let i = 0, a = arra[0], b = arrb[0]; i <= this.data.trace.length; i++, a = arra[i], b = arrb[i]) {
      const latlng = this.mapMiddle(a as [number, number], b as [number, number])
      let edge = edges.pop();
      if (!edge) {
        edge = new EdgeMarker(this, this.tmp_layer)
      }
      edge.update(i, latlng.lat, latlng.lng)
      this.edges.push(edge)
    }
    edges.forEach((edge) => edge.delete())
  }

  mapMiddle(a: LatLngExpression, b: LatLngExpression) {
    return this.map.map.layerPointToLatLng(this.map.map.latLngToLayerPoint(a).add(this.map.map.latLngToLayerPoint(b)).divideBy(2));
  }

  static create(map: ParcoursMap, start: MarkerController, end: MarkerController, index: number) {
    const segment = map.data.createSegment(start.data, end.data, index);
    const controller = new SegmentController(map, segment);
    (window as any).segment = controller

    map.data.selectSegment(segment.id);
    return controller
  }
}

class EdgeMarker {
  private marker
  private fromIndex?: number
  private created = false
  constructor(private segment: SegmentController, private tmpLayer: LayerGroup) {
    this.marker = marker([0, 0],
      {
        draggable: true,
        icon: divIcon({
          className: "vertex-handle middle",
        }),
        contextmenu: false,
        contextmenuItems: []
      }).addTo(this.tmpLayer);


    this.marker.on('drag', (event) => {
      if (this.fromIndex === undefined) return
      if (!this.created) {
        this.segment.addVertex(this.fromIndex, this.marker.getLatLng().lat, this.marker.getLatLng().lng)
        this.created = true
      } else {
        this.segment.modifyVertex(this.fromIndex, this.marker.getLatLng().lat, this.marker.getLatLng().lng)
      }
    })
    this.marker.on('dragstart', (e) => {
      segment.dragging = 'edge'
    })
    this.marker.on('dragend', (e) => {
      segment.updateMarkers()
      delete segment.dragging
    })
  }

  update(fromIndex: number, lat: number, lng: number) {
    this.fromIndex = fromIndex
    this.created = false
    this.marker.setLatLng([lat, lng])
  }

  delete() {
    this.marker.remove()
  }
}

class VertexMarker {
  private marker: Marker
  private index?: number
  constructor(private segment: SegmentController, private tmpLayer: LayerGroup) {
    this.marker = marker([0, 0],
      {
        draggable: true,
        icon: divIcon({
          className: "vertex-handle",
        }),
        contextmenu: false,
        contextmenuItems: []
      }).addTo(this.tmpLayer);

    this.marker.on('drag', (e) => {
      if (this.index === undefined) return
      this.segment.modifyVertex(this.index, this.marker.getLatLng().lat, this.marker.getLatLng().lng)
    })
    this.marker.on('dblclick', (e) => {
      if (this.index === undefined) return
      this.segment.removeVertex(this.index)
    })
    this.marker.on('dragstart', (e) => {
      segment.dragging = 'vertex'
    })
    this.marker.on('dragend', (e) => {
      delete segment.dragging
    })
  }

  update(index: number, lat: number, lng: number) {
    this.index = index
    this.marker.setLatLng([lat, lng])
  }

  delete() {
    this.marker.remove()
  }
}