import { LitElement, html, css, unsafeCSS, HTMLTemplateResult } from "lit";
import { ref, createRef, Ref } from 'lit/directives/ref.js';
import { customElement, property } from "lit/decorators.js";
import { repeat } from "lit/directives/repeat.js";
import { ifDefined } from "lit/directives/if-defined.js";
import 'nice-forms.css'
import formCss from 'inline:../node_modules/nice-forms.css/dist/nice-forms.css'


export interface FieldGroup {
  type: 'group'
  name: string
  label: string
  description?: string
  fields: Exclude<Field, FieldGroup>[]
}

export interface BaseField<T, type> {
  type: type
  name: string
  label: string
  value?: T
  /**function called on fields update */
  updater?: (value: T) => void
}

interface OpenField<T, type> extends BaseField<T, type> {
  required?: boolean
  placeholder?: string
}

export interface StringField extends OpenField<string, 'string'> {
  autocomplete?: 'off'
}

export interface NumberField extends OpenField<number, 'number'> {
  autocomplete?: 'off',
  precision?: number
}

export interface BooleanField extends BaseField<boolean, 'boolean'> { }

export interface TextField extends OpenField<string, 'text'> { }

export interface FileField extends BaseField<any, 'file'> { }

export type Field = FieldGroup | StringField | TextField | FileField | NumberField | BooleanField

@customElement('lit-form')
export class LitForm extends LitElement {
  static styles = [
    unsafeCSS(formCss),
    //css`fieldset{border: 0;}`,
    css`
      /* W3.CSS 4.15 December 2020 by Jan Egil and Borge Refsnes */
      :host{box-sizing:border-box}
      *,*:before,*:after{box-sizing:inherit}
    `
  ]
  @property({ attribute: false }) fields: Field[] = []
  @property({ type: Boolean }) noSubmit: boolean = false
  @property({ attribute: false }) onSubmit: (fields: Field[], data: { [k: string]: FormDataEntryValue }, event: Event) => void = () => { }

  private fields_ref: { [k: string]: Ref<HTMLInputElement> } = {}

  renderField(field: Field) {
    switch (field.type) {
      case 'group':
        return this.renderFieldGroup(field);
      case 'string':
        return this.renderStringField(field);
      case 'text':
        return this.renderTextField(field);
      case 'number':
        return this.renderNumberField(field)
      case 'file':
        return this.renderFileField(field)
      case 'boolean':
        return this.renderBooleanField(field)
      default:
        break;
    }
  }
  renderBooleanField(field: BooleanField) {
    this.fields_ref[field.name] = createRef()
    return html`
            <div class="nice-form-group">
                <input ${ref(this.fields_ref[field.name])} @input=${(e: Event) => field.updater?.((e.target as HTMLInputElement).checked)} id="${field.name}" type="checkbox" name="${field.name}" ?checked="${field.value}" />
                <label for="${field.name}" >${field.label}</label>
            </div>
        `
  }
  setBoolean(name: string, value: boolean) {
    if (name in this.fields_ref && this.fields_ref[name].value && this.fields_ref[name].value.checked != value) {
      this.fields_ref[name].value.checked = value
      return true
    } else {
      return false
    }
  }

  renderNumberField(field: NumberField) {
    this.fields_ref[field.name] = createRef()
    return html`
        <div class="nice-form-group">
            <label>${field.label}</label>
            <input 
              ${ref(this.fields_ref[field.name])}
              name=${field.name}
              id=${field.name}
              @input=${(e: Event) => field.updater?.(parseFloat((e.target as HTMLInputElement).value))} 
              type="number" 
              value=${ifDefined(field.value?.toPrecision(field.precision))} 
              step=${10 ** (-(field.precision ?? 1) + 1)} 
              placeholder=${ifDefined(field.placeholder)} 
              ?required=${field.required} />
        </div>`
  }
  setNumber(name: string, value: number) {
    if (name in this.fields_ref && this.fields_ref[name].value && parseFloat(this.fields_ref[name].value.value) != value) {
      this.fields_ref[name].value.value = value.toString()
      return true
    } else {
      return false
    }
  }

  renderStringField(field: StringField): HTMLTemplateResult {
    this.fields_ref[field.name] = createRef()
    return html`
            <div class="nice-form-group" style="">
                <label for="${field.name}">${field.label}</label>
                <input ${ref(this.fields_ref[field.name])} @input=${(e: Event) => field.updater?.((e.target as HTMLInputElement).value)} id="${field.name}" type="text" name=${field.name} autocomplete=${ifDefined(field.autocomplete)} value=${ifDefined(field.value)} placeholder=${ifDefined(field.placeholder)} ?required=${field.required} />
            </div>
        `
  }
  setString(name: string, value: string) {
    if (name in this.fields_ref && this.fields_ref[name].value && this.fields_ref[name].value.value != value) {
      this.fields_ref[name].value.value = value
      return true
    } else {
      return false
    }
  }

  renderTextField(field: TextField): HTMLTemplateResult {
    console.warn('file field not totally implemented');

    return html`
            <div class="col-span-full">
                <label for="${field.name}" class="block text-sm/6 font-medium text-gray-900">${field.label}</label>
                <div class="mt-2">
                    <textarea id="${field.name}" name="${field.name}" rows="3" class="block w-full rounded-md bg-white px-3 py-1.5 text-base text-gray-900 outline-1 -outline-offset-1 outline-gray-300 placeholder:text-gray-400 focus:outline-2 focus:-outline-offset-2 focus:outline-indigo-600 sm:text-sm/6"></textarea>
                </div>
            </div>
        `
  }

  renderFileField(field: FileField): HTMLTemplateResult {
    console.warn('file field not totally implemented');

    return html`
            <div class="nice-form-group">
                <label for="${field.name}">${field.label}</label>
                <input name="${field.name}" id="${field.name}" type="file" />
            </div>
        `
  }

  renderFieldGroup(field: FieldGroup): HTMLTemplateResult {
    return html`
        <fieldset class="nice-form-group">
            <legend>${field.label}</legend>
            ${repeat(field.fields, field => field.name, field => this.renderField(field))}
        </fieldset>
        `
  }

  updateFields(data: { [k: string]: FormDataEntryValue }, fields: Field[]) {
    for (let field of fields) {
      if (field.type === 'group') {
        this.updateFields(data, field.fields)
      } else if (field.name in data) {
        field.value = data[field.name]
        switch (field.type) {
          case 'number':
            field.value = parseFloat(data[field.name] as any)
            break;

          default:
            field.value = data[field.name]
            break;
        }
      }
    }
  }

  submitCallback(event: SubmitEvent) {
    event.preventDefault()
    const form = event.target as HTMLFormElement
    const data = Object.fromEntries(new FormData(form).entries())

    this.updateFields(data, this.fields)
    this.onSubmit(this.fields, data, event)
    return false
  }

  render() {
    console.debug('render fields ', this.fields);

    return html`
            <form @submit=${this.submitCallback}>
                <div>
                    ${repeat(this.fields, field => field.name, field => this.renderField(field))}
                </div>
                ${!this.noSubmit ? html`
                  <br>
                  <button type="submit" class="rounded-md bg-white px-3 py-2 text-sm font-semibold text-gray-900 shadow-xs inset-ring inset-ring-gray-300 hover:bg-gray-50">enregistrer</button>
                `: undefined}
            </form> 
        `;
  }
}