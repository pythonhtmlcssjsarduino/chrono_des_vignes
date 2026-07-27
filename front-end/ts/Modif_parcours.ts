import { html, render } from "lit";
import "./map_ui";
import { ParcoursData } from "./parcours_data.js";

const div = document.getElementById('parcours')

if (!div) {
  throw new Error("#parcours div not found");
}

const event_id = parseInt(div.dataset.event_id || '')
const parcours_id = parseInt(div.dataset.parcours_id || '')

if (!event_id || !parcours_id) {
  throw new Error("ids not found");
}

let data = await ParcoursData.fetch(event_id, parcours_id);

let template = html`
    <parcours-map .data=${data} width="100%"></parcours-map>
`

render(template, document.getElementById('parcours')!)