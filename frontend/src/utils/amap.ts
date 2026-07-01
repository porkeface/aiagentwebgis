import AMapLoader from '@amap/amap-jsapi-loader'

let _AMap: typeof AMap | null = null
let _loadPromise: Promise<typeof AMap> | null = null

/**
 * Load the Amap JS API 2.0 SDK exactly once.
 *
 * The Amap key is read from VITE_AMAP_KEY. You must also register the key's
 * "Web端(JS API)" service in the Amap console with the app's origin.
 * https://console.amap.com/dev/key/app
 */
export function loadAMap(): Promise<typeof AMap> {
  if (_AMap) return Promise.resolve(_AMap)
  if (_loadPromise) return _loadPromise

  const key = import.meta.env.VITE_AMAP_KEY as string | undefined
  if (!key) {
    throw new Error(
      'VITE_AMAP_KEY is not set. Create a .env file with VITE_AMAP_KEY=your-key',
    )
  }

  // Required by Amap since 2021-12 for keys registered for Web端(JS API)
  ;(window as unknown as Record<string, unknown>)._AMapSecurityConfig = {
    securityJsCode: '',
  }

  _loadPromise = AMapLoader.load({
    key,
    version: '2.0',
  })
    .then((amap: typeof AMap) => {
      _AMap = amap
      return amap
    })
    .catch((err: unknown) => {
      _loadPromise = null
      throw err
    })

  return _loadPromise
}

/** Get the already-loaded AMap instance (null if not loaded yet). */
export function getAMap(): typeof AMap | null {
  return _AMap
}
