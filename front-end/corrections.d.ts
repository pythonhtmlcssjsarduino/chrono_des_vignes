import 'leaflet'
import 'leaflet-contextmenu'

declare module 'leaflet' {
    interface Marker {
        bindContextMenu(options: { contextmenu?: boolean; contextmenuItems?: ContextMenuItem[]; }): this;
    }

    interface Layer {
        bindContextMenu(options: { contextmenu?: boolean; contextmenuItems?: ContextMenuItem[]; }): this;
    }

    interface Map {
        contextmenu: {
            showAt(latlng: LatLng): void;
            hide(): void;
            addItem(options: any): void;
            removeItem(item: any): void;
        };
    }

    interface MapOptions {
        contextmenu?: boolean;
        contextmenuItems?: ContextMenuItem[];
    }
    interface MarkerOptions {
        contextmenu?: boolean;
        contextmenuItems?: ContextMenuItem[];
    }
}