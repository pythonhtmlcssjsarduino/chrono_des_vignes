import { html, render } from "lit";
import "./parcours_map";
import { ParcoursData } from "./parcours_data";

declare global {
  interface Window {
    event_id: number;
    parcours_id: number;
  }
}
let data = await ParcoursData.fetch(window.event_id, window.parcours_id)
console.log(data);
(globalThis as any).data = data

let template = html`
    <parcours-map .data=${data} width="100%"></parcours-map>
`

render(template, document.getElementById('parcours')!)