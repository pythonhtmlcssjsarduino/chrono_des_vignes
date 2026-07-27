import { LitElement, html, css } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { Runner, RunnerEvents } from '../run_data/runner';
import { GestionEvents, RunControllerM } from '../run_data/run_controller';
import { DateTime, Duration } from 'luxon';
import { Receiver } from '../recever'
import 'iconify-icon';

@customElement('runner-card')
export class RunnerCard extends LitElement {
  @property({ type: Object })
  public runner!: Runner;

  @property({ type: Object })
  public gestion!: RunControllerM;

  @property({ type: Number })
  public parcoursId!: number;

  @state()
  private duration: Duration | null = null; // Temps écoulé en ms
  @state()
  private lastPassageDuration: Duration | null = null;

  private runnerReciver!: Receiver<RunnerEvents>
  private tickReciver!: Receiver<GestionEvents>
  private detailOpen: boolean = false;

  connectedCallback(): void {
    super.connectedCallback();
    this.runnerReciver = new Receiver(this.runner, 'update')
    this.tickReciver = new Receiver(this.gestion, 'tick',
      (now: DateTime) => {
        this.duration = this.runner.elapsedTime;
        this.lastPassageDuration = this.runner.lastPassage ? now.diff(this.runner.lastPassage.timestamp) : null;
      }
    )
    this.subscribe();
  }

  disconnectedCallback(): void {
    super.disconnectedCallback();
    this.runnerReciver.unsubscribe()
    this.tickReciver.unsubscribe()
  }

  private subscribe() {
    this.runnerReciver.subscribe((reason) => {
      if (reason === 'passage' || reason === 'status') {
        this.requestUpdate();

        if (reason == 'status' && this.runner.statusOverride == 'running') {
          this.tickReciver.subscribe()
        }
        if (reason == 'status' && this.runner.statusOverride != 'running') {
          this.tickReciver.unsubscribe()
          this.duration = this.runner.elapsedTime;
          //this.lastPassageDuration = this.runner.lastPassage ? now.diff(this.runner.lastPassage.timestamp) : null;

        }
      }
    });

    // 2. Écouter le tick global pour le chrono si le coureur est en course
    if (this.runner.status === 'running') {
      console.log(this.tickReciver);

      this.tickReciver.subscribe()
    } else if (this.runner.status != 'pending') {
      this.duration = this.runner.elapsedTime;
      //this.lastPassageDuration = this.runner.lastPassage ? now.diff(this.runner.lastPassage.timestamp) : null;

    }

  }

  private toggleDetail() {
    this.detailOpen = !this.detailOpen;
    this.requestUpdate();
  }

  private async handleAction(newStatus: 'disqualified' | 'abandoned' | 'finished') {
    const currentStatus = this.runner.status;

    // Cas 1 : On clique sur le statut DÉJÀ actif -> On propose de RÉINITIALISER (Remettre en course)
    if (newStatus === currentStatus) {
      const confirmMsg = `Le coureur est déjà marqué comme "${newStatus}". Voulez-vous le remettre en course ?`;
      if (!confirm(confirmMsg)) return;

      await this.gestion.setRunnerStatus(this.runner.id, null);
      return;
    }

    // Cas 2 : On change de statut (ex: Pending -> Disqual, ou Disqual -> Finish)
    // Action directe, pas de confirmation pour gagner du temps, sauf si on passe de Finished à autre chose (optionnel)
    if (currentStatus !== 'pending') {
      if (!confirm("Attention : Ce coureur a déjà validé l'arrivée. Êtes-vous sûr de vouloir modifier son statut ?")) {
        return;
      }
    }

    await this.gestion.setRunnerStatus(this.runner.id, newStatus);
  }

  private handleSingleStart() {
    if (confirm('Démarrer ce coureur maintenant ?')) {
      this.gestion.startRunner(this.parcoursId, this.runner.id);
    }
  }

  render() {
    if (!this.runner) return html``;

    const status = this.runner.status;
    const isRunning = status === 'running';
    const isPending = status === 'pending';
    const isFinished = status === 'finished';
    const isDQ = status === 'disqualified';
    const isAbandon = status === 'abandoned';
    console.log(isPending);

    // Détermination de la classe CSS selon le statut
    const statusClass = {
      'pending': 'bg-info',
      'running': 'bg-primary',
      'finished': 'bg-success',
      'disqualified': 'bg-danger',
      'abandoned': 'bg-warning',
      'absent': 'bg-secondary'
    }[status] || 'bg-light';

    return html`
      <div class="card ${statusClass}">
        <div class="card-header">
          <div class="identity">
            <span class="bib">${this.runner.bibNumber}</span>
            <span class="name">${this.runner.firstName} ${this.runner.lastName}</span>
          </div>
          <div class="top-actions">
            ${isPending
        ? html`<button class="btn-icon btn-start" @click=${this.handleSingleStart} title="Démarrer seul"><iconify-icon icon="mdi:stopwatch-start"></iconify-icon></iconify-icon></button>`
        : ''
      }
            <button class="btn-icon" @click=${this.toggleDetail}>
              <iconify-icon icon="mdi:chevron-${this.detailOpen ? 'up' : 'down'}"></iconify-icon>
            </button>
          </div>
        </div>

        <div class="card-body">
          <div class="chrono-display">
            ${this.duration !== null
        ? html`<span>${this.duration < Duration.fromObject({ days: 1 }) ? this.duration.toFormat("h:m:s") : this.duration.toFormat("d 'days' h:m:s")}</span>`
        : html`<span class="waiting">En attente</span>`
      }
          </div>
          
          <div class="last-stand">
            ${this.runner.lastPassage
        ? html`<small>Dernier: ${this.runner.lastPassage.standName} (${this.lastPassageDuration?.toFormat('hh:mm:ss') || '-'})</small>`
        : ''
      }
          </div>
        </div>

        ${this.detailOpen ? html`
          <div class="card-details">
            <div class="actions-grid">
              <button 
                  class="btn btn-sm btn-danger ${isDQ ? 'active-state' : ''}" 
                  @click=${() => this.handleAction('disqualified')}
                  title="${isDQ ? 'Cliquez pour remettre en course' : 'Disqualifier'}">
                  <iconify-icon icon="mdi:cancel" class="icon"></iconify-icon>
                  <span>Disqualifier</span>
                </button>

                <!-- Bouton Abandon -->
                <button 
                  class="btn btn-sm btn-warning ${isAbandon ? 'active-state' : ''}" 
                  @click=${() => this.handleAction('abandoned')}
                  title="${isAbandon ? 'Cliquez pour remettre en course' : 'Marquer abandon'}">
                  <iconify-icon icon="mdi:walk" class="icon"></iconify-icon>
                  <span>Abandon</span>
                </button>

                <!-- Bouton Arrivée -->
                <button 
                  class="btn btn-sm btn-success ${isFinished ? 'active-state' : ''}" 
                  @click=${() => this.handleAction('finished')}
                  title="${isFinished ? 'Cliquez pour modifier' : 'Valider l\'arrivée'}">
                  <iconify-icon icon="mdi:flag-checkered" class="icon"></iconify-icon>
                  <span>Arrivée</span>
                </button>

            </div>
            
            <div class="passages-list">
              <h4>Passages</h4>
              <table>
                <thead><tr><th>Stand</th><th>Heure</th><th>Delta</th></tr></thead>
                <tbody>
                  ${[...this.runner.passages].reverse().map(p => html`
                    <tr>
                      <td>${p.standName}</td>
                      <td>${p.timestamp.toLocaleString(DateTime.DATETIME_MED_WITH_SECONDS)}</td>
                      <td>${p.deltaMs !== null ? (p.deltaMs / 1000).toFixed(1) + 's' : '-'}</td>
                    </tr>
                  `)}
                </tbody>
              </table>
            </div>
          </div>
        ` : ''}
      </div>
    `;
  }

  static styles = css`
    .card { border-radius: 8px; overflow: hidden; box-shadow: 0 2px 5px rgba(0,0,0,0.1); transition: transform 0.2s; color: white; }
    .card-header { padding: 1rem; display: flex; justify-content: space-between; align-items: center; background: rgba(0,0,0,0.1); }
    .identity { display: flex; align-items: center; gap: 0.5rem; font-weight: bold; }
    .bib { background: white; color: #333; padding: 2px 6px; border-radius: 4px; font-size: 0.9rem; }
    .card-body { padding: 1rem; text-align: center; background: rgba(255,255,255,0.1); }
    .chrono-display { font-size: 2rem; font-family: monospace; font-weight: bold; margin-bottom: 0.5rem; }
    .waiting { font-size: 1.2rem; opacity: 0.8; }
    .last-stand { font-size: 0.85rem; opacity: 0.9; }
    
    .card-details { padding: 1rem; background: white; color: #333; }
    .actions-grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 0.5rem; margin-bottom: 1rem; }
    .btn { border: none; padding: 0.4rem; border-radius: 4px; cursor: pointer; font-size: 0.8rem; color: white; }
    .btn-sm { font-size: 0.75rem; }
    .btn-danger { background: #e74c3c; }
    .btn-warning { background: #f39c12; color: #333; }
    .btn-success { background: #2ecc71; }
    .btn:disabled { opacity: 0.5; cursor: not-allowed; filter: grayscale(1); }
    
    table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
    th, td { padding: 4px; text-align: left; border-bottom: 1px solid #eee; }
    th { color: #7f8c8d; }

    .btn-icon { background: none; border: none; color: white; cursor: pointer; font-size: 1.1rem; padding: 0 4px; }
    .btn-start { color: #fff; text-shadow: 0 0 2px black; }

    /* Couleurs de fond utilitaires */
    .bg-info { background-color: #3498db; }
    .bg-primary { background-color: #2980b9; } /* Un peu plus foncé pour le texte blanc */
    .bg-success { background-color: #27ae60; }
    .bg-danger { background-color: #c0392b; }
    .bg-warning { background-color: #f39c12; color: #333 !important; }
    .bg-secondary { background-color: #95a5a6; }


    .actions-grid { 
      display: grid; 
      grid-template-columns: 1fr 1fr 1fr; 
      gap: 0.5rem; 
      margin-bottom: 1rem; 
    }

    .btn { 
      border: 2px solid transparent;
      padding: 0.4rem 0.2rem; 
      border-radius: 6px; 
      cursor: pointer; 
      font-size: 0.75rem; 
      color: white; 
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: 4px;
      transition: all 0.2s ease;
      opacity: 0.9;
      background-color: var(--btn-bg, #ccc); /* Fallback */
    }
    
    /* Couleurs spécifiques */
    .btn-danger { background-color: #e74c3c; }
    .btn-warning { background-color: #f39c12; color: #333; }
    .btn-success { background-color: #2ecc71; }

    .btn:hover { opacity: 1; transform: translateY(-1px); }
    .btn:active { transform: translateY(0); }

    /* STYLE ÉTAT ACTIF */
    .active-state {
      outline: 3px solid rgba(0, 0, 0, 0.5);
      transform: scale(1.05);
      opacity: 1;
      font-weight: bold;
      box-shadow: 0 4px 8px rgba(0,0,0,0.3);
      z-index: 1; /* Pour passer au dessus des voisins si besoin */
    }
    
    .btn:disabled { 
      opacity: 0.4; 
      cursor: not-allowed; 
      filter: grayscale(1); 
      transform: none !important;
      outline: none !important;
    }

    /* Style spécifique pour Iconify */
    .icon {
      font-size: 1.4rem; /* Taille de l'icône */
      width: 1em;
      height: 1em;
      /* L'icône prendra automatiquement la couleur du texte (color: white ou #333) défini sur le bouton */
    }
    
    span {
      line-height: 1.1;
    }
  `;
}