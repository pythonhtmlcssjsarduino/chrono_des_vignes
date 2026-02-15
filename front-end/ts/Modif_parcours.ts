import { html, render } from "lit";
import "./map_ui";
import { ParcoursData } from "./parcours_data";

declare global {
  interface Window {
    event_id: number;
    parcours_id: number;
  }
}
let data = await ParcoursData.fetch(window.event_id, window.parcours_id);
(globalThis as any).data = data

let template = html`
    <parcours-map .data=${data} width="100%"></parcours-map>
`

render(template, document.getElementById('parcours')!)