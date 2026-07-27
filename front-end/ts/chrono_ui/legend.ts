import { LitElement, html, css } from 'lit';
import { customElement } from 'lit/decorators.js';

@customElement('timing-legend')
export class TimingLegend extends LitElement {
  static styles = css`
    :host {
      display: flex;
      justify-content: center;
      gap: 1rem;
      padding: 0.5rem;
      background: #fff;
      border-top: 1px solid #ddd;
      font-size: 0.75rem;
      flex-wrap: wrap;
    }
    .badge {
      display: flex;
      align-items: center;
      gap: 0.3rem;
    }
    .dot {
      width: 10px;
      height: 10px;
      border-radius: 50%;
      display: inline-block;
    }
  `;

  render() {
    const items = [
      { color: '#28a745', label: 'Valide' },
      { color: '#dc3545', label: 'Dossard Invalide' },
      { color: '#fd7e14', label: 'Pas Départ' },
      { color: '#6f42c1', label: 'Doublon' },
      { color: '#007bff', label: 'Modifié Manuel' },
      { color: '#343a40', label: 'Erreur Serveur' },
      { color: '#adb5bd', label: 'En Attente' },
    ];

    return html`
      ${items.map(item => html`
        <div class="badge">
          <span class="dot" style="background-color: ${item.color}"></span>
          ${item.label}
        </div>
      `)}
    `;
  }
}