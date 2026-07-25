import { html, render } from 'lit';
import { customElement, property } from 'lit/decorators.js';
import { RunControllerM } from './run_data/run_controller';
import './run_ui/app-shell';

const div = document.getElementById('app');
if (!div) throw new Error('App root element not found');

const edition_id = parseInt(div.dataset.edition_id || '');
const event_id = parseInt(div.dataset.event_id || '');

if (isNaN(edition_id) || isNaN(event_id)) {
  throw new Error(`Invalid edition or event ID("${div.dataset.edition_id}", "${div.dataset.event_id}")`);
}

const gestion = new RunControllerM(edition_id, event_id);
(gestion as any).startTickLoop();
(gestion as any).startRealTimeSync()

render(html`<app-shell .gestion=${gestion}></app-shell>`, div);