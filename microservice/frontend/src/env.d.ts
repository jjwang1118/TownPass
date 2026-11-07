/// <reference types="vite/client" />

declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<object, object, unknown>
  export default component
}

interface FlutterObject {
  postMessage: (message: string) => void
  addEventListener: (type: 'message', listener: (event: MessageEvent) => void) => void
  removeEventListener: (type: 'message', listener: (event: MessageEvent) => void) => void
}

interface DetectedBarcode {
  rawValue: string
}

interface BarcodeDetectorInstance {
  detect: (source: CanvasImageSource) => Promise<DetectedBarcode[]>
}

interface Window {
  flutterObject?: FlutterObject
  BarcodeDetector?: new (options?: { formats: string[] }) => BarcodeDetectorInstance
}
