import { LitElement, html, css } from 'lit';
import { customElement, property } from 'lit/decorators.js';
import { TimingAction } from '../chrono_data/types';
import { SyncEngine } from '../chrono_data/sync-engine';
import { ifDefined } from 'lit/directives/if-defined.js';

interface HistoryAction {
  name: string,
  action: (action: TimingAction, syncEngine: SyncEngine) => void;
  style?: string;
}


@customElement('timing-history')
export class TimingHistory extends LitElement {
  @property({ type: Array }) actions: TimingAction[] = [];
  @property({ type: Number }) selectedId: number | null = null;
  @property({ type: Object }) syncEngine!: SyncEngine;

  static readonly HistoryActions: Record<string, HistoryAction> = {
    /**duplicate: {
      name: 'duplicate',
      action(action, syncEngine) {

      },
    },*/
    /**edit_bib: {
      name: 'Editer le dossard',
      action(action, syncEngine) {

      },
    },*/
    edit_time: {
      name: 'Ajuster le temps',
      action(action, syncEngine) {

      },
    },
    delete: {
      name: 'Supprimer',
      action(action, syncEngine) {

      },
      style: 'color: red;'
    },
  }

  static styles = css`
    :host {
      display: flex;
      flex-direction: column;
      height: 100%;
      overflow: hidden;
    }
    .header {
      padding: 1rem;
      font-weight: bold;
      background: #f8f9fa;
      border-bottom: 1px solid #ddd;
    }
    .list-container {
      flex: 1;
      overflow-y: auto; /* Scrollbar native */
      padding: 0.5rem;
    }
    .item {
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-direction: column;
      padding: 0.75rem;
      margin-bottom: 0.5rem;
      border-radius: 6px;
      cursor: pointer;
      border-left: 5px solid transparent;
      background: #fff;
      box-shadow: 0 1px 3px rgba(0,0,0,0.05);
      transition: transform 0.1s;
    }
    .item:hover { transform: translateX(2px); }
    .item.selected { outline: 2px solid #007bff; }
    
    /* Codes Couleurs (Bordure gauche + Fond léger) */
    .status-valid { border-left-color: #28a745; background: #f0fff4; }
    .status-invalid_bib { border-left-color: #dc3545; background: #fff5f5; }
    .status-bib_not_started { border-left-color: #fd7e14; background: #fff8f0; }
    .status-duplicate { border-left-color: #6f42c1; background: #f8f0ff; }
    .status-manual_override { border-left-color: #007bff; background: #f0f7ff; }
    .status-server_error { border-left-color: #343a40; background: #f1f1f1; }
    .status-pending, .status-error { border-left-color: #adb5bd; background: #fff; opacity: 0.8; }

    .item-content { flex: 1; }
    .bib-number { font-weight: bold; font-size: 1.1rem; }
    .time-display { font-family: monospace; font-size: 0.9rem; color: #555; }
    .status-msg { font-size: 0.8rem; color: #666; }
    
    .menu-btn {
      background: none; border: none; font-size: 1.2rem; cursor: pointer; color: #666;
      padding: 0 5px;
    }
    
    /* Menu drawer Simple  open at the bottom of the standard infos*/

    .drawer-panel button {
      width: 100%; 
      padding: 8px 12px;
      border: none; 
      background: none;
      cursor: pointer;
      font-size: 0.9rem;
    }
    .drawer-panel button:hover { background: #f0f0f0; }
  `;

  private getStatusClass(action: TimingAction): string {
    switch (action.status) {
      case 'synced': return 'status-valid';
      case 'pending': return 'status-pending';
      case 'error':
        switch (action.error_type) {
          case 'bib_not_started':
            return 'status-bib_not_started'
          case 'invalid_bib':
            return 'status-invalid_bib'
          default:
            return 'status-server_error';
        }

      default: return 'status-error';
    }
  }

  private handleActionClick(id: number) {
    console.log('click', id);

    this.dispatchEvent(new CustomEvent('select', { detail: { id } }));
    this.selectedId = this.selectedId === id ? null : id;
  }

  connectedCallback() {
    super.connectedCallback();
    // Fermer le menu si on clique ailleurs
    //window.addEventListener('click', this.handleOutsideClick);
    this.syncEngine.on('QueueUpdated', (queue) => {
      this.actions = queue;
      this.requestUpdate();
    });
  }

  render() {
    // Limiter l'affichage aux 50 derniers pour la perf
    const displayActions = this.actions.slice(0, 50);

    return html`
      <div class="header">Historique en temps réel</div>
      <div class="list-container">
        ${displayActions.map(action => html`
          <div 
            class="item ${this.getStatusClass(action)} ${this.selectedId === action.id ? 'selected' : ''}"
            @click=${() => this.handleActionClick(action.id)}
          >
            <div class="item-content">
              <div class="bib-number">Dossard: ${action.bib}</div>
              <div class="time-display">
                ${action.timestamp.toFormat('d/MM/yyyy HH:mm:ss.SSS')}
                ${action.status === 'pending' ? '⏳' : ''}
                ${action.status === 'error' ? '⚠️' : ''}
              </div>
              <div class="status-msg">
                ${action.status === 'synced' ? 'Validé' : action.error_message || 'En attente...'}
              </div>
            </div>
            
            ${this.selectedId === action.id ? html`
              <hr style="width:100%; border:none; border-top:1px solid #ddd; margin:0.5rem 0;">
              <div class="drawer-panel">
                ${Object.entries(TimingHistory.HistoryActions).map(([key, actionDef]) => html`
                  <button style=${ifDefined(actionDef.style)} @click=${(e: Event) => actionDef.action(action, this.syncEngine)}>${actionDef.name}</button>
                `)}
               </div>
            ` : ''}
          </div>
        `)}
        ${this.actions.length === 0 ? html`<div style="text-align:center; color:#999; margin-top:2rem;">Aucun historique</div>` : ''}
      </div>
    `;
  }
}