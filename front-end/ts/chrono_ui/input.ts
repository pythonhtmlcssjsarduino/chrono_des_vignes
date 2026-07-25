import { LitElement, html, css } from 'lit';
import { customElement, state, query, property } from 'lit/decorators.js';
import { DateTime } from 'luxon';
import type { SyncEngine } from '../chrono_data/sync-engine';

@customElement('timing-input')
export class TimingInput extends LitElement {
  @query('#main-input') private inputEl!: HTMLInputElement;
  @state() private pendingTimes: DateTime[] = [];
  @state() private syncEngine!: SyncEngine;

  static styles = css`
    :host {
      display: flex;
      flex-direction: column;
      padding: 1rem;
      background: #fff;
      border-bottom: 1px solid #eee;
    }
    .input-group {
      position: relative;
      display: flex;
      gap: 0.5rem;
    }
    input {
      width: 50px;
      flex: 1;
      padding: 0.75rem;
      font-size: 1.2rem;
      border: 2px solid #ddd;
      border-radius: 6px;
      outline: none;
      transition: border-color 0.2s;
    }
    input:focus {
      border-color: #007bff;
    }
    button {
      padding: 0 1rem;
      background: #007bff;
      color: white;
      border: none;
      border-radius: 6px;
      cursor: pointer;
      font-weight: bold;
    }
    button:hover { background: #0056b3; }
    .hint {
      font-size: 0.8rem;
      color: #888;
      margin-top: 0.5rem;
    }
  `;

  connectedCallback() {
    super.connectedCallback();
    // Focus automatique global
    document.addEventListener('keydown', (e) => this.handleKeyDown(e));
    this.syncEngine.on('PendingTimesUpdated', (times: DateTime[]) => {
      this.pendingTimes = times;
      this.requestUpdate();
    });
  }

  firstUpdated() {
    this.inputEl.focus();
  }

  private handleKeyDown(e: KeyboardEvent) {
    // Optionnel : Ignorer si la touche est maintenue (autorepeat)
    if (e.repeat) return;
    // Si on tape Espace et que l'input est vide (ou focus ailleurs), on capture un temps "Now"
    if (e.code === 'Space') {
      e.preventDefault();
      this.capturePendingTime();
    }
    // Esc pour supprimer le dernier temps en attente (si input vide)
    else if (e.code === 'Escape' && this.inputEl.value.trim() === '') {
      e.preventDefault();
      this.deleteLastPending();
    }
    // Entrée pour valider l'action
    else if (e.code === 'Enter') {
      e.preventDefault();
      this.submitAction();
    }
  }

  private capturePendingTime() {

    const now = DateTime.now();
    this.syncEngine.addPendingTime(now);
    this.flashInput('#28a745');
  }

  private deleteLastPending() {
    this.syncEngine.popLastPendingTime();
  }

  private submitAction() {
    const rawValue = this.inputEl.value;
    if (!rawValue.trim()) return;

    // Parsing puissant (nettoyage espaces, tabs)
    const cleanValue = rawValue.replace(/\s+/g, ' ').trim();

    // check if it is a valid bib number (simple regex for digits)
    if (!/^\d+$/.test(cleanValue)) {
      // alerte visuelle flash rouge
      this.flashInput('#dc3545');
      return;
    }

    // TODO: Logique de parsing avancée (détection auto dossard vs temps)
    // Hypothèse: l'utilisateur tape "34" pour attribuer au dernier temps en attente
    // ou "34 15:30:00" pour forcer un temps.

    const bib = parseInt(cleanValue);
    const lastTime = this.syncEngine.popLastPendingTime();

    if (!lastTime) {
      this.flashInput('#ffc107'); // Avertissement: pas de temps en attente
      return;
    }

    // Appel au moteur de synchro
    this.syncEngine.addAction(bib, lastTime);

    this.inputEl.value = '';
    this.inputEl.focus();
  }

  private flashInput(color: string) {
    this.inputEl.style.backgroundColor = color;
    setTimeout(() => this.inputEl.style.backgroundColor = '#ddd', 300);
  }

  render() {
    return html`
      <div class="input-group">
        <input 
          id="main-input" 
          type="text" 
          placeholder="Saisir dossard" 
          autocomplete="off"
        >
        <button @click=${this.submitAction}>Valider</button>
      </div>
      <div class="hint">
        <code>Espace</code>: Capturer temps maintenant | 
        <code>Entrée</code>: Valider | 
        <code>Esc</code>: Annuler dernier temps
      </div>
      ${this.pendingTimes.length > 0
        ? html`<div style="margin-top:0.5rem; font-size:0.9em; color:#007bff;">
            ${this.pendingTimes.length} temps en attente d'attribution
          </div>`
        : ''}
    `;
  }
}

