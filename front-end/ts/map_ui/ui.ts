import { Control, DomUtil } from "leaflet";

export class InfoBar extends Control {
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