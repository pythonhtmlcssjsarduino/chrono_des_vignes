import { DefaultEvents, Emitter, EventsMap, Unsubscribe, EmitterMixin } from 'nanoevents'

export class Receiver<Events extends EventsMap = DefaultEvents, K extends keyof Events = keyof Events> {
  private subscription?: Unsubscribe

  constructor(
    private emitter: EmitterMixin<Events>,
    private event: K,
    private callback?: Events[K]
  ) {
    console.log('init', this.emitter != undefined);
  }

  subscribe(callback?: Events[K]) {
    if (this.subscription) return

    if (callback) {
      this.callback = callback
    }

    if (!this.callback) return
    this.subscription = this.emitter.on(this.event, this.callback)
  }

  unsubscribe() {
    if (!this.subscription) return

    this.subscription()
    this.subscription = undefined
  }
}