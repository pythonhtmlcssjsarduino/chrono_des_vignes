import { LitElement, html, css } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { createNanoEvents, Emitter } from 'nanoevents';

// --- TYPES ---

interface Assignment {
  id: string;
  parcours: string;
  stand: string;
}

interface KeyData {
  passages: number;
  id: number;
  name: string;
  code: string;
  assignments: Assignment[];
}

interface UpdatePayload {
  id: number;
  name?: string;
  assignments?: Assignment[];
}

interface DeletePayload {
  id: number;
}

interface EventsMap {
  update: (data: UpdatePayload) => void;
  delete: (data: DeletePayload) => void;
}

// --- COMPOSANT ENFANT : cdv-key-card ---

@customElement('cdv-key-card')
class CdvKeyCard extends LitElement {
  static styles = css`
        :host {
            display: block;
            background: white;
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            padding: 16px;
            margin-bottom: 12px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
            font-family: sans-serif;
        }
        .header { 
            display: flex; 
            justify-content: space-between; 
            align-items: center; 
            margin-bottom: 12px; 
            border-bottom: 1px solid #f0f0f0; 
            padding-bottom: 8px; 
            user-select: none; /* Empêche la sélection du texte lors du clic rapide */
        }
        .header-content { display: flex; flex-direction: row; gap: 12px; }
        .name-display { font-weight: bold; font-size: 1.1rem; color: #333; cursor: pointer; padding: 4px 8px; border-radius: 4px; display: inline-block; }
        .name-display:hover { background-color: #f5f5f5; }
        .name-input { font-weight: bold; font-size: 1.1rem; padding: 4px 8px; border: 1px solid #009688; border-radius: 4px; width: 200px; }
        
        .code-display { 
            font-family: monospace; 
            background: #f0f4f8; 
            padding: 2px 8px; 
            border-radius: 4px; 
            font-size: 0.8rem; 
            color: #546e7a; 
            border: 1px solid #cfd8dc;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            width: fit-content;
        }
        .code-display:hover { background: #eceff1; border-color: #b0bec5; }

        .btn-delete { background: none; border: none; cursor: pointer; color: #999; transition: color 0.2s; display: flex; align-items: center; padding: 4px; }
        .btn-delete:hover { color: #d32f2f; background: #ffebee; border-radius: 4px; }
        
        /* Liste des assignments */
        .assignments-list { margin-top: 12px; display: flex; flex-direction: column; gap: 8px; }
        .assignment-row { display: flex; align-items: center; gap: 8px; background: #f9f9f9; padding: 8px; border-radius: 6px; border: 1px solid #eee; }
        .assignment-tag { display: inline-flex; align-items: center; gap: 6px; background: #e0f2f1; color: #00695c; padding: 4px 8px; border-radius: 4px; font-size: 0.85rem; font-weight: 500; }
        .assignment-tag.stand { background: #e3f2fd; color: #1565c0; }
        
        .btn-remove-assign { background: none; border: none; cursor: pointer; color: #ef5350; padding: 4px; display: flex; align-items: center; justify-content: center; margin-left: auto; }
        .btn-remove-assign:hover { background: #ffebee; border-radius: 50%; }
        
        /* Formulaire d'ajout */
        .add-form { display: flex; gap: 8px; align-items: center; margin-top: 12px; padding-top: 12px; border-top: 1px dashed #ddd; flex-wrap: wrap; }
        .add-form select { flex: 1; min-width: 120px; padding: 6px; border-radius: 4px; border: 1px solid #ddd; font-size: 0.9rem; }
        .btn-add { background: #009688; color: white; border: none; border-radius: 4px; padding: 6px 12px; cursor: pointer; font-weight: bold; display: flex; align-items: center; gap: 4px; white-space: nowrap; }
        .btn-add:hover { background: #00796b; }
        .btn-add:disabled { background: #cfd8dc; cursor: not-allowed; }

        iconify-icon { font-size: 18px; }
        .empty-state { color: #999; font-size: 0.9rem; font-style: italic; margin-top: 8px; }

         .code-display { 
            font-family: monospace; 
            background: #f0f4f8; 
            padding: 2px 8px; 
            border-radius: 4px; 
            font-size: 0.8rem; 
            color: #546e7a; 
            border: 1px solid #cfd8dc;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            height: fit-content;
            transition: all 0.2s ease; /* Transition douce pour le changement de couleur */
            user-select: none; /* Empêche la sélection du texte lors du clic rapide */
        }
        .code-display:hover { background: #eceff1; border-color: #b0bec5; }
        
        /* Style spécifique quand c'est copié */
        .code-display.copied-success {
            background: #e8f5e9;
            border-color: #2e7d32;
        }

    `;

  @property({ type: Number }) keyId: number = 0;
  @property({ type: String }) keyName: string = "Nouvelle Clé";
  @property({ type: String }) keyCode: string = "";
  @property({ type: Array }) assignments: Assignment[] = [];
  @property({ type: Number }) passagesCount: number = 0;
  @state() private _copied: boolean = false;

  @state() private parcoursData!: EditionData
  @state() private availableParcours: string[] = [];

  @state() private _isEditing: boolean = false;
  @state() private _tempName: string = "";
  @state() private _newParcours: string = "";
  @state() private _newStand: string = "";
  @state() private _availableStandsForNew: string[] = [];

  private emitter = createNanoEvents<EventsMap>()

  public on<K extends keyof EventsMap>(event: K, callback: EventsMap[K]) {
    this.emitter.on(event, callback);
  }

  protected firstUpdated() {
    // Initialize available parcours based on initial assignments
    const assignedParcours = this.assignments.map(a => a.parcours);
    this.availableParcours = this.parcoursData.parcours.map(p => p.name).filter(p => !assignedParcours.includes(p));
  }

  protected updated(changedProperties: Map<string, unknown>) {
    super.updated(changedProperties);
    if (changedProperties.has('_isEditing') && this._isEditing) {
      requestAnimationFrame(() => {
        const input = this.shadowRoot?.querySelector('.name-input') as HTMLInputElement;
        if (input) {
          input.focus();
          try { input.select(); } catch (e) { }
        }
      });
    }
  }

  private startEditing() {
    this._isEditing = true;
    this._tempName = this.keyName;
  }

  private saveName(e: Event) {
    const input = this.shadowRoot?.querySelector('.name-input') as HTMLInputElement;
    if (!input) return;
    const newName = input.value.trim();

    if (newName) {
      this.keyName = newName;
      this.emitter.emit('update', { id: this.keyId, name: newName });
    } else {
      this.keyName = this._tempName;
    }
    this._isEditing = false;
  }

  private handleDelete() {
    // todo : show a better confirmation dialog
    // todo : suplementary confirmation if the edition is near the run date
    if (confirm(`Voulez-vous vraiment supprimer la clé "${this.keyName}" (${this.keyCode}) ?`)) {
      this.emitter.emit('delete', { id: this.keyId });
    }
  }

  private handleNewParcoursChange(e: Event) {
    const val = (e.target as HTMLSelectElement).value;
    this._newParcours = val;
    this._newStand = "";

    this._availableStandsForNew = this.parcoursData.parcours.find(p => p.name === val)?.chrono_stands.map(s => s.name) || [];
  }

  private handleNewStandChange(e: Event) {
    this._newStand = (e.target as HTMLSelectElement).value;
  }

  private addAssignment() {
    if (!this._newParcours || !this._newStand) return;

    const newAssignment: Assignment = {
      id: Date.now().toString(),
      parcours: this._newParcours,
      stand: this._newStand
    };

    const newAssignments = [...this.assignments, newAssignment];
    this.emitter.emit('update', { id: this.keyId, assignments: newAssignments });

    this._newParcours = "";
    this._newStand = "";
    this._availableStandsForNew = [];
    this.availableParcours = this.availableParcours.filter(p => p !== newAssignment.parcours);
  }

  private removeAssignment(assignmentId: string) {
    const assignment = this.assignments.find(a => a.id === assignmentId);
    const newAssignments = this.assignments.filter(a => a.id !== assignmentId);
    this.emitter.emit('update', { id: this.keyId, assignments: newAssignments });
    this.availableParcours = [...this.availableParcours, assignment!.parcours];
  }
  private copyCode() {
    if (this.keyCode) {
      navigator.clipboard.writeText(this.keyCode);

      // Activation du feedback visuel
      this._copied = true;

      // Désactivation après 2 secondes
      setTimeout(() => {
        this._copied = false;
      }, 2000);
    }
  }


  render() {
    return html`
            <div class="header">
                <div class="header-content">
                    ${this._isEditing
        ? html`<input class="name-input" .value=${this._tempName} @blur=${this.saveName} @keydown=${(e: KeyboardEvent) => {
          if (e.key === 'Enter') this.saveName(e);
          if (e.key === 'Escape') { this.keyName = this._tempName; this._isEditing = false; }
        }} />`
        : html`<span class="name-display" @dblclick=${this.startEditing} title="Double-cliquez pour modifier le nom"><iconify-icon icon="mdi:key-wireless" width="24" height="24"></iconify-icon> ${this.keyName}</span>`
      }
                    
                    ${this.keyCode ? html`
                        <span class="code-display" @click=${this.copyCode} title="Cliquez pour copier le code">
                            ${this._copied
          ? html`
                                    <iconify-icon icon="mdi:check-circle" style="margin-right:4px; color: #2e7d32;"></iconify-icon>
                                    <span style="color: #2e7d32; font-weight: bold;">Copié !</span>
                                  `
          : html`
                                    <iconify-icon icon="mdi:key-variant" style="margin-right:4px;"></iconify-icon>
                                    ${this.keyCode}
                                  `
        }
                        </span>
                    ` : html`<span class="empty-state">Aucun code</span>`}
                </div>

                <button class="btn-delete" @click=${this.handleDelete} title=${this.passagesCount === 0 ? "Supprimer la clé" : "Clé utilisée suppression impossible"} ?disabled=${this.passagesCount > 0} >
                    <iconify-icon icon="mdi:trash-can-outline"></iconify-icon> 

                </button>
            </div>

            ${this.assignments.length > 0 ? html`
                <div class="assignments-list">
                    ${this.assignments.map(assign => html`
                        <div class="assignment-row">
                            <div class="assignment-tag">
                                <iconify-icon icon="mdi:map-marker-path"></iconify-icon>
                                ${assign.parcours}
                            </div>
                            <iconify-icon icon="mdi:arrow-right-thin" style="color:#999"></iconify-icon>
                            <div class="assignment-tag stand">
                                <iconify-icon icon="mdi:flag"></iconify-icon>
                                ${assign.stand}
                            </div>
                            <button class="btn-remove-assign" @click=${() => this.removeAssignment(assign.id)} title=${this.passagesCount === 0 ? "Retirer" : "Clé utilisée suppression impossible"} ?disabled=${this.passagesCount > 0}>
                                <iconify-icon icon="mdi:close"></iconify-icon>
                            </button>
                        </div>
                    `)}
                </div>
            ` : html`<div class="empty-state">Aucun parcours assigné.</div>`}

            <div class="add-form">
                <select @change=${this.handleNewParcoursChange} .value=${this._newParcours} style="flex: 1; min-width: 100px;" >
                    <option value="" disabled>Parcours...</option>
                    ${this.availableParcours.map(p => html`<option value=${p}>${p}</option>`)}
                </select>
                
                <select @change=${this.handleNewStandChange} .value=${this._newStand} ?disabled=${!this._newParcours} style="flex: 1; min-width: 100px;">
                    <option value="" disabled>Stand...</option>
                    ${this._availableStandsForNew.map(s => html`<option value=${s}>${s}</option>`)}
                </select>

                <button class="btn-add" @click=${this.addAssignment} ?disabled=${!this._newParcours || !this._newStand}>
                    <iconify-icon icon="mdi:plus"></iconify-icon>
                    Ajouter
                </button>
            </div>
        `;
  }
}

// --- COMPOSANT PARENT : cdv-container ---

interface EditionData {
  name: string;
  edition_date: string;
  description: string;
  first_inscription: string;
  last_inscription: string;
  rdv_lat: number;
  rdv_lng: number;
  parcours: ParcoursData[];
}
interface ParcoursData {
  name: string;
  description: string;
  chrono_stands: StandData[];
}
interface StandData {
  name: string;
  lat: number;
  lng: number;
  id: number;
}


@customElement('cdv-container')
class CdvContainer extends LitElement {
  static styles = css`
        :host { display: block; }
        .list-wrapper { display: flex; flex-direction: column; gap: 8px; margin-bottom: 15px; }
        .btn-container { display: flex; justify-content: center; width: 100%; margin-top: 10px; }
        .btn-plus {
            background: white; border: 1px solid #ddd; border-radius: 50%;
            width: 40px; height: 40px; display: flex; justify-content: center;
            align-items: center; cursor: pointer; box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            transition: all 0.2s ease; color: #009688;
        }
        .btn-plus:hover { background: #009688; color: white; transform: scale(1.05); }
        iconify-icon { font-size: 24px; }
    `;

  @property({ type: Number }) eventId: number = 0
  @property({ type: Number }) editionId: number = 0

  @state() private isLoading: boolean = true;
  @state() keys: KeyData[] = [];

  private _cardRefs: Map<number, CdvKeyCard> = new Map()
  private editionData!: EditionData;

  async firstUpdated() {
    const editionResponse = await fetch(apiUrl('edition', 'v1', `/get_edition/${this.editionId}/${this.eventId}`));
    const edition_data = await editionResponse.json();
    this.editionData = edition_data;
    console.log("Edition Data:", this.editionData);

    const keysResponse = await fetch(apiUrl('passages', 'v1', `/list_keys/${this.editionId}/${this.eventId}`));
    const keys_data = await keysResponse.json();
    this.keys = keys_data.keys.map((k: any) => ({
      id: k.id,
      name: k.name,
      code: k.key,
      passages: k.passages,
      assignments: k.stands.map((s: any) => ({
        id: s.id,
        parcours: s.parcours,
        stand: s.name
      }))
    }));
    this.isLoading = false;
  }

  updated() {
    this.keys.forEach(key => {
      const cardId = key.id;
      const cardEl = this.shadowRoot?.querySelector(`cdv-key-card[key-id="${cardId}"]`) as CdvKeyCard | null;

      if (cardEl && !this._cardRefs.has(cardId)) {
        cardEl.on('delete', (data) => this._handleDelete(data));
        cardEl.on('update', (data) => this._handleUpdate(data));
        this._cardRefs.set(cardId, cardEl);
      }
    });

    for (const [id] of this._cardRefs.entries()) {
      if (!this.keys.find(k => k.id === id)) {
        this._cardRefs.delete(id);
      }
    }
  }

  private async _addKey() {
    const newId = Date.now();

    const newKey: KeyData = {
      id: newId,
      name: `Clé ${this.keys.length + 1}`,
      code: '',
      passages: 0,
      assignments: []
    };
    this.keys = [...this.keys, newKey];

    // create the key server-side
    const payload = {
      name: newKey.name
    };
    const response = await fetch(apiUrl('passages', 'v1', `/create_key/${this.eventId}/${this.editionId}`), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(payload)
    });
    const data = await response.json();

    // Update the key with the real ID and code from the server
    this.keys = this.keys.map(k => {
      if (k.id === newId) {
        return { ...k, id: data.id, code: data.key };
      }
      return k;
    });
  }

  private async _handleDelete(data: DeletePayload) {
    this.keys = this.keys.filter(k => k.id !== data.id);
    const response = await fetch(apiUrl('passages', 'v1', `/delete_key/${data.id}`), {
      method: 'DELETE'
    });
    if (!response.ok || (await response.json()).success != true) {
      alert("Erreur lors de la suppression de la clé.");
      location.reload()
    }
  }

  private async _handleUpdate(data: UpdatePayload) {
    this.keys = this.keys.map(k => {
      if (k.id === data.id) {
        return { ...k, ...data };
      }
      return k;
    });
    console.log(data);

    const payload = {
      id: data.id,
      name: data.name,
      stands_ids: data.assignments?.map(a => this.editionData.parcours.find(p => a.parcours === p.name)!.chrono_stands.find(s => s.name === a.stand)!.id)
    }
    const response = await fetch(apiUrl('passages', 'v1', `/edit_key`), {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(payload)
    });
    if (!response.ok || (await response.json()).success != true) {
      alert("Erreur lors de la mise à jour de la clé.");
      location.reload()
    }

  }

  render() {

    if (this.isLoading) {
      return html`
        <div class="loading-container">
          <h3>Chargement des clés de chronométrage...</h3>
        </div>
      `;
    }

    return html`
            <div class="list-wrapper">
                ${this.keys.map(key => html`
                    <cdv-key-card
                        key-id="${key.id}"
                        .keyId=${key.id}
                        .keyName=${key.name}
                        .keyCode=${key.code}
                        .assignments=${key.assignments}
                        .passagesCount=${key.passages}
                        .parcoursData=${this.editionData}
                    ></cdv-key-card>
                `)}
            </div>
            
            <div class="btn-container">
                <button class="btn-plus" @click=${this._addKey}>
                    <iconify-icon icon="mdi:plus"></iconify-icon>
                </button>
            </div>
        `;
  }
}

export { CdvContainer, CdvKeyCard };

declare global {
  interface HTMLElementTagNameMap {
    "cdv-key-card": CdvKeyCard;
    "cdv-container": CdvContainer;
  }
}