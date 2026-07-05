import { StorageService as IStorageService } from './storage.interface';
import { LocalStorageService } from './storage-local.impl';
import storageAvailable from 'storage-available';

// Singleton
class StorageServiceContainer {
  private static instance: IStorageService;

  static getInstance(): IStorageService {
    if (!StorageServiceContainer.instance) {
      // Par défaut, on utilise le LocalStorage
      if (!storageAvailable('localStorage')) {
        throw new Error('LocalStorage non disponible. Le stockage local est requis pour cette application.');
      }
      StorageServiceContainer.instance = new LocalStorageService();

      // FUTUR TAURI:
      // if (window.__TAURI__) {
      //   StorageServiceContainer.instance = new TauriStorageService();
      // }
    }
    return StorageServiceContainer.instance;
  }
}


export const StorageService = StorageServiceContainer.getInstance();