/**
 * Utility to manage saved views, filter presets, and column visibilities for data tables.
 */

interface SavedView {
  id: string
  name: string
  filters: Record<string, any>
  columnOrder: string[]
  sortBy: string
  sortOrder: 'asc' | 'desc'
}

const STORAGE_PREFIX = "saved_view:"

export const saveViewPreset = (targetPage: string, preset: SavedView): void => {
  try {
    const listRaw = localStorage.getItem(`${STORAGE_PREFIX}list:${targetPage}`)
    const list: string[] = listRaw ? JSON.parse(listRaw) : []
    
    if (!list.includes(preset.id)) {
      list.push(preset.id)
      localStorage.setItem(`${STORAGE_PREFIX}list:${targetPage}`, JSON.stringify(list))
    }
    
    localStorage.setItem(`${STORAGE_PREFIX}preset:${preset.id}`, JSON.stringify(preset))
  } catch (error) {
    console.error("Error saving view preset:", error)
  }
}

export const loadViewPresets = (targetPage: string): SavedView[] => {
  try {
    const listRaw = localStorage.getItem(`${STORAGE_PREFIX}list:${targetPage}`)
    if (!listRaw) return []
    
    const list: string[] = JSON.parse(listRaw)
    const presets: SavedView[] = []
    
    for (const id of list) {
      const presetRaw = localStorage.getItem(`${STORAGE_PREFIX}preset:${id}`)
      if (presetRaw) {
        presets.push(JSON.parse(presetRaw))
      }
    }
    return presets;
  } catch (error) {
    console.error("Error loading view presets:", error)
    return []
  }
}

export const deleteViewPreset = (targetPage: string, id: string): void => {
  try {
    const listRaw = localStorage.getItem(`${STORAGE_PREFIX}list:${targetPage}`)
    if (listRaw) {
      const list: string[] = JSON.parse(listRaw)
      const updated = list.filter(item => item !== id)
      localStorage.setItem(`${STORAGE_PREFIX}list:${targetPage}`, JSON.stringify(updated))
    }
    localStorage.removeItem(`${STORAGE_PREFIX}preset:${id}`)
  } catch (error) {
    console.error("Error deleting view preset:", error)
  }
}
