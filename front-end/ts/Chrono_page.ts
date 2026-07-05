import { LitElement, html, css } from 'lit';
import { customElement, property, query, state } from 'lit/decorators.js';
import { SyncEngine } from './chrono_data/sync-engine';
import { SyncState } from './chrono_data/types';
import './chrono_ui/input';
import './chrono_ui/history';
import './chrono_ui/legend';
import { DateTime } from 'luxon';
import { BlackBoxLogService as BlackBoxLog } from './chrono_data/BlackBoxLog';
import { LocalStorageService } from './chrono_data/storage-local.impl';

(window as any).DateTime = DateTime

@customElement('timing-page')
export class TimingPage extends LitElement {

  @query('#export-type') private exportSelect!: HTMLSelectElement;
  @state() private syncState: SyncState = { is_online: true, queue_length: 0, last_sync: null };
  @state() private pendingTimes: DateTime[] = [];
  @property({ type: String, useDefault: false }) readonly KEY: string = ''
  private syncEngine = new SyncEngine();


  static styles = css`
    :host {
      display: flex;
      flex-direction: column;
      height: 100%;
      width: 100%;
      overflow: hidden;
      font-family: system-ui, -apple-system, sans-serif;
      background-color: #f4f4f9;
    }
    header {
      padding: 0.5rem 1rem;
      background: #fff;
      border-bottom: 1px solid #ddd;
      display: flex;
      justify-content: space-between;
      align-items: center;
      height: 50px;
    }
    .status-badge {
      font-size: 0.85rem;
      padding: 0.25rem 0.5rem;
      border-radius: 4px;
      font-weight: bold;
    }
    .status-online { background: #e6fffa; color: #047857; }
    .status-offline { background: #fff5f5; color: #c53030; }

    /* Conteneur gauche (Titre + Export) */
    .header-left {
      display: flex;
      align-items: center;
      gap: 1rem;
    }

    /* Séparateur vertical */
    .header-divider {
      border-left: 1px solid #ddd;
      height: 20px;
      margin: 0 0.5rem;
    }

    /* Groupe d'export (select + btn) */
    .export-group {
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }

    /* Style du select */
    .export-select {
      padding: 0.25rem 0.5rem;
      font-size: 0.85rem;
      border-radius: 4px;
      border: 1px solid #ccc;
      background: #fff;
      cursor: pointer;
      outline: none;
    }

    .export-select:focus {
      border-color: #007bff;
    }

    /* Style du bouton */
    .export-btn {
      padding: 0.25rem 0.75rem;
      font-size: 0.85rem;
      background-color: #007bff;
      color: white;
      border: none;
      border-radius: 4px;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 0.4rem;
      transition: background-color 0.2s;
    }

    .export-btn:hover {
      background-color: #0056b3;
    }

    .export-btn svg {
      width: 14px;
      height: 14px;
    }
    
    main {
      display: flex;
      flex: 1;
      overflow: hidden; /* Important pour que les enfants gèrent leur scroll */
    }
    .left-pane {
      flex: 1;
      display: flex;
      flex-direction: column;
      border-right: 1px solid #ddd;
      min-width: 410px;
      max-width: 500px;
      background: #fff;
    }
    .right-pane {
      flex: 2;
      display: flex;
      flex-direction: column;
      background: #fafafa;
      position: relative;
    }
  `;

  connectedCallback() {
    super.connectedCallback();
    // Initialisation du moteur de synchro
    this.syncEngine.init(this.KEY);

    // Subscription aux changements d'état
    this.syncEngine.on('update', (state) => {
      this.syncState = state;
    });
    this.syncEngine.on('PendingTimesUpdated', (times: DateTime[]) => {
      this.pendingTimes = times;
      this.requestUpdate();
    });
  }

  private async handleExport() {
    const type = this.exportSelect.value;
    var blob;
    switch (type) {
      case 'full_log':
        blob = await this.syncEngine.logger.exportFullFile()
        BlackBoxLog.download(blob, `chrono_blackbox_${new Date().toISOString()}.json`);
        break;
      case 'raw_log':
        BlackBoxLog.download(await this.syncEngine.logger.exportRawFile(), `chrono_blackbox_${new Date().toISOString()}.bin`);
        break;
      case 'pending_times':
        const pendingData = this.pendingTimes.map(dt => dt.toISO());
        blob = new Blob([JSON.stringify(pendingData, null, 2)], { type: 'application/json' });
        BlackBoxLog.download(blob, `pending_times_${new Date().toISOString()}.json`);
        break;
      case 'full_actions':
        const fullActions = this.syncEngine.getQueue().map(action => LocalStorageService.serializeTimingAction(action));
        blob = new Blob([JSON.stringify(fullActions, null, 2)], { type: 'application/json' });
        BlackBoxLog.download(blob, `full_actions_${new Date().toISOString()}.json`);
        break;

      default:
        console.warn('Type d\'export inconnu:', type);
    }
  }

  render() {
    return html`
      <header><!-- GAUCHE : Titre + Export -->
        <div class="header-left">
          <div>
            <strong>Chrono des Vignes</strong> 
            <span class="event-label">Événement: Test</span>
          </div>

          <!-- Séparateur -->
          <div class="header-divider"></div>

          <!-- Groupe Export -->
          <div class="export-group">
            <select id="export-type" class="export-select">
              <option value="pending_times">passage en attente</option>
              <option value="full_actions">toutes les passages</option>
              <option value="full_log">Journal Complet(json)</option>
              <option value="raw_log">Journal Brut(binaire)</option>
            </select>
            
            <button @click=${this.handleExport} class="export-btn">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                <polyline points="7 10 12 15 17 10"></polyline>
                <line x1="12" y1="15" x2="12" y2="3"></line>
              </svg>
              Exporter
            </button>
          </div>
        </div>

        <!-- DROITE : Statut -->
        <div class="status-badge ${this.syncState.is_online ? 'status-online' : 'status-offline'}">
          ${this.syncState.is_online ? '● En ligne' : '● Hors ligne'}
          ${!this.syncState.is_online && this.syncState.queue_length > 0
        ? html` <span class="pending-count">(${this.syncState.queue_length} en attente)</span>`
        : ''}
        </div>
      </header>

      <main>
        <!-- Zone Gauche : Saisie & Temps en attente (Front-only) -->
        <div class="left-pane">
          <timing-input .syncEngine=${this.syncEngine}></timing-input>
          
          <!-- Liste des temps "pré-enregistrés" (Front-only, non persistés si non validés) -->
          <div style="flex:1; overflow-y:auto; padding:1rem;">
            <h3 style="margin-top:0; color:#555;">Temps en attente d'attribution</h3>
            ${this.pendingTimes.length === 0
        ? html`<p style="color:#888; font-size:0.9em; font-style:italic;">Aucun temps en attente. Appuyez sur <code>Espace</code>.</p>`
        : this.pendingTimes.map((time, index) => {
          // Formatage direct ici
          const formatted = time.isValid ? time.toFormat('d/MM/yyyy HH:mm:ss.SSS') : 'Erreur';

          return html`
                        <div 
                          key=${index} 
                          style="
                            display: flex;
                            justify-content: space-between;
                            align-items: center;
                            padding: 0.75rem 1rem;
                            margin-bottom: 0.5rem;
                            background-color: #e3f2fd;
                            border: 1px solid #90caf9;
                            border-left: 5px solid #2196f3;
                            border-radius: 4px;
                            font-family: 'Courier New', monospace;
                            font-size: 1.1rem;
                            font-weight: 600;
                            color: #1565c0;
                            cursor: pointer;
                            transition: transform 0.1s, background-color 0.2s;
                            user-select: none;
                          "
                          @click=${() => void 0}
                          @mouseenter=${(e: any) => e.target.style.transform = 'translateX(4px)'}
                          @mouseleave=${(e: any) => e.target.style.transform = 'translateX(0)'}
                        >
                          <span>${formatted}</span>
                          <!-- <span style="font-size:0.8rem; opacity:0.7; font-family:system-ui;">Cliquez pour attribuer</span> -->
                        </div>
                      `;
        })
      }
          </div>
        </div>

        <!-- Zone Droite : Historique & Détails -->
        <div class="right-pane">
          <timing-history 
            .syncEngine=${this.syncEngine}>
          </timing-history>

          <timing-legend></timing-legend>
        </div>
      </main>
    `;
  }
}