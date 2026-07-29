import pkg from '../../package.json'

export const APP_VERSION = pkg.version
export const APP_NAME = '企业智能体工作台'

export function formatVersionLabel(version = APP_VERSION) {
  return `v${version}`
}
