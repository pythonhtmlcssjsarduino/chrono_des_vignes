import { html, render } from "lit";
import { Field, LitForm } from "./forms";
import "./forms"

const form = document.getElementById('form')!

const fields: Field[] = [
  { type: 'string', name: 'name', label: 'nom', value: 'stand.name' },
  { type: 'boolean', name: 'chrono', label: 'chrono', value: true },

  {
    type: 'group', name: 'latlng', label: 'test', fields: [
      { type: 'number', name: 'lat', label: 'latitude', value: 35 },
      { type: 'number', name: 'lng', label: 'longitude', value: 345 }
    ]
  }
]

function submit(fields: Field[], data: { [k: string]: FormDataEntryValue }) {
  console.log(data, fields);
}

const d = html`<lit-form .fields=${fields} .onSubmit=${submit
  }></lit-form>`


render(d, form)