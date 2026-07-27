import { ParcoursMap } from "./map.js";

export default ParcoursMap

declare global {
  interface HTMLElementTagNameMap {
    "parcours-map": ParcoursMap
  }
}