import { LitElement, html, css } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { RunControllerM } from '../run_data/run_controller';
import { ParcoursState } from '../run_data/parcours_state';
import './parcours-panel';
import './legends-panel';

@customElement('app-shell')
export class AppShell extends LitElement {
  @property({ type: Object })
  public gestion!: RunControllerM;

  @state()
  private activeParcoursId: number | null = null;

  @state()
  private sseConnected: boolean = false;

  @state()
  private parcoursList: ParcoursState[] = [];

  connectedCallback(): void {
    super.connectedCallback();
    if (!this.gestion) return;

    // Abonnements aux événements globaux
    this.gestion.emitter.on('sse:status', (connected) => {
      this.sseConnected = connected;
      this.requestUpdate();
    });

    this.gestion.emitter.on('parcours:loaded', (id) => {
      this.refreshParcoursList();
      if (this.activeParcoursId === null) {
        this.activeParcoursId = id;
      }
      this.requestUpdate();
    });

    // Si les stats changent (badges), on refresh la liste des onglets
    // Note: Dans une app complexe, on aurait un store dédié pour la liste, 
    // ici on refresh simplement le tableau de référence.
  }

  private refreshParcoursList() {
    this.parcoursList = this.gestion.getAllParcours();
  }

  private switchTab(id: number) {
    this.activeParcoursId = id;
  }

  render() {
    if (this.parcoursList.length === 0) {
      return html`<div class="container"><p>Aucun parcours configuré.</p></div>`;
    }

    const activeParcours = this.parcoursList.find(p => p.id === this.activeParcoursId);

    return html`
      <header class="top-bar">
        <div class="brand">Chrono des Vignes</div>
        <div class="status-indicator ${this.sseConnected ? 'connected' : 'disconnected'}">
          <span class="dot"></span>
          ${this.sseConnected ? 'En direct' : 'Déconnecté'}
        </div>
      </header>

      <nav class="tabs-nav">
        ${this.parcoursList.map(p => {
      const stats = p.stats;
      const isActive = p.id === this.activeParcoursId;
      return html`
            <button 
              class="tab ${isActive ? 'active' : ''}" 
              @click=${() => this.switchTab(p.id)}>
              ${p.name}
              <span class="badge">${stats.running}/${stats.total}</span>
            </button>
          `;
    })}
  
      </nav>

      <main class="content">
        ${activeParcours
        ? html`<parcours-panel .parcours=${activeParcours} .gestion=${this.gestion}></parcours-panel>`
        : html`<div>Sélectionnez un parcours</div>`
      }
      </main>

      <legends-panel></legends-panel>
      
    `;
  }

  static styles = css`
    :host { display: block; height: 100%; display: flex; flex-direction: column; font-family: sans-serif; }
    .top-bar { display: flex; flex: 0 0 auto; justify-content: space-between; padding: 1rem; background: #2c3e50; color: white; align-items: center; }
    .brand { font-weight: bold; font-size: 1.2rem; }
    .status-indicator { font-size: 0.9rem; display: flex; align-items: center; gap: 0.5rem; }
    .dot { width: 10px; height: 10px; border-radius: 50%; display: inline-block; }
    .connected .dot { background-color: #2ecc71; box-shadow: 0 0 5px #2ecc71; }
    .disconnected .dot { background-color: #e74c3c; }
    
    .tabs-nav { display: flex; background: #ecf0f1; overflow-x: auto; border-bottom: 1px solid #bdc3c7; }
    .tab { flex: 1; padding: 1rem;min-width: 120px; border: none; background: transparent; cursor: pointer; font-weight: 600; color: #7f8c8d; position: relative; white-space: nowrap; }
    .tab.active { color: #2c3e50; background: white; }
    .tab.active::after { content: ''; position: absolute; bottom: 0; left: 0; right: 0; height: 3px; background: #3498db; }
    .badge { background: #3498db; color: white; padding: 2px 6px; border-radius: 10px; font-size: 0.8rem; margin-left: 8px; }
    
    .content { overflow-y: auto; flex: 1; padding: 1rem; background: #f9f9f9; }
    legends-panel { 
      flex: 0 0 auto;
      position: sticky; /* Ou fixed si vous voulez qu'elle flotte par dessus */
      bottom: 0; }
  `;
}