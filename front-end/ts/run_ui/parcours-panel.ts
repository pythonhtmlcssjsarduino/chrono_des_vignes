import { LitElement, html, css } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { ParcoursState } from '../run_data/parcours_state';
import { RunControllerM } from '../run_data/run_controller';
import './runner-card';

@customElement('parcours-panel')
export class ParcoursPanel extends LitElement {
  @property({ type: Object })
  public parcours!: ParcoursState;

  @property({ type: Object })
  public gestion!: RunControllerM;

  @state()
  private isLaunching: boolean = false; // Pour le compte à rebours UI

  @state()
  private launchCountdown: number | null = null;

  private launchTimer: number | null = null;

  connectedCallback(): void {
    super.connectedCallback();
    // S'abonner aux changements de stats de CE parcours pour mettre à jour les boutons
    if (this.parcours) {
      this.parcours.emitter.on('stats-change', () => this.requestUpdate());
      // S'abonner à l'ajout de runner si dynamique (optionnel selon implémentation)
      this.parcours.emitter.on('runner-update', () => this.requestUpdate());
    }
  }

  disconnectedCallback(): void {
    super.disconnectedCallback();
    if (this.launchTimer !== null) {
      window.clearInterval(this.launchTimer);
      this.launchTimer = null;
    }
  }

  private async handleLaunchAll() {
    if (this.isLaunching) return;

    this.isLaunching = true;
    this.launchCountdown = 3;

    this.launchTimer = window.setInterval(async () => {
      if (this.launchCountdown === null) return;
      this.launchCountdown -= 1;

      if (this.launchCountdown < 0) {
        if (this.launchTimer !== null) {
          window.clearInterval(this.launchTimer);
          this.launchTimer = null;
        }

        try {
          await this.gestion.launchParcours(this.parcours.id);
        } finally {
          this.isLaunching = false;
          this.launchCountdown = null;
        }
      }
    }, 1000);
  }

  private handleStop() {
    if (confirm('Arrêter le parcours pour tous les coureurs restants ?')) {
      this.gestion.stopParcours(this.parcours.id);
    }
  }

  render() {
    return html`
      <div class="panel-header">
        <h2>${this.parcours.name}</h2>
        <div class="actions">
          <button id="btn-launch" class="btn btn-primary" @click=${this.handleLaunchAll} ?disabled=${!this.parcours.launchable || this.isLaunching}>
            ${this.launchCountdown === null
        ? 'Lancer le parcours'
        : this.launchCountdown < 0
          ? 'GO!'
          : `${this.launchCountdown}...`
      }
          </button>
          <button class="btn btn-danger" @click=${this.handleStop} ?disabled=${this.parcours.stats.running === 0}>
          Arrêter le parcours
          </button>
        </div>
      </div>

      <div class="runners-grid">
        ${Array.from(this.parcours.runners.values()).map(runner => html`
          <runner-card 
            .runner=${runner} 
            .gestion=${this.gestion}
            .parcoursId=${this.parcours.id}>
          </runner-card>
        `)}
      </div>
    `;
  }

  static styles = css`
    .panel-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem; background: white; padding: 1rem; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    h2 { margin: 0; color: #2c3e50; }
    .actions { display: flex; gap: 1rem; }
    .btn { padding: 0.6rem 1.2rem; border: none; border-radius: 4px; font-weight: bold; cursor: pointer; transition: opacity 0.2s; }
    .btn:disabled { opacity: 0.6; cursor: not-allowed; }
    .btn-primary { background: #3498db; color: white; }
    .btn-danger { background: #e74c3c; color: white; }
    
    .runners-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 1rem; }
  `;
}