import 'leaflet'
import 'leaflet-contextmenu'

declare module 'leaflet' {
    interface Marker {
        bindContextMenu(options: {contextmenu?: boolean;contextmenuItems?: ContextMenuItem[];}): this;
    }

    // Si vous voulez aussi l'ajouter à d'autres couches (comme L.Circle, L.Polygon, etc.)
    interface Layer {
        bindContextMenu(options: {contextmenu?: boolean; contextmenuItems?: ContextMenuItem[];}): this;
    }
}