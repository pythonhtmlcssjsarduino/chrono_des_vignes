import { LitElement, html, css } from 'lit';
import { customElement } from 'lit/decorators.js';

@customElement('legends-panel')
export class LegendsPanel extends LitElement {
  render() {
    return html`
      <div class="legend">
        <h4>Légende</h4>
        <ul>
          <li><span class="dot bg-danger"></span> Disqualifié / Abandon</li>
          <li><span class="dot bg-success"></span> Arrivé (Correct)</li>
          <li><span class="dot bg-warning"></span> Arrivé (Hors parcours / Manuel)</li>
          <li><span class="dot bg-primary"></span> En course</li>
          <li><span class="dot bg-info"></span> En attente de départ</li>
        </ul>
      </div>
    `;
  }

  static styles = css`
    .legend { background: white; padding: 1rem; margin-top: 2rem; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); font-size: 0.9rem; }
    h4 { margin-top: 0; color: #2c3e50; }
    ul { list-style: none; padding: 0; margin: 0; display: flex; flex-wrap: wrap; gap: 1rem; }
    li { display: flex; align-items: center; gap: 0.5rem; }
    .dot { width: 12px; height: 12px; border-radius: 50%; display: inline-block; }
    .bg-danger { background: #c0392b; }
    .bg-success { background: #27ae60; }
    .bg-warning { background: #f39c12; }
    .bg-primary { background: #2980b9; }
    .bg-info { background: #3498db; }
  `;
}