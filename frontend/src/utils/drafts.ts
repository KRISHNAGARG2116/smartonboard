/**
 * Helper utility to manage local auto-saving of drafts for long form inputs.
 */

export const saveDraft = (key: string, data: any): void => {
  try {
    const payload = {
      timestamp: Date.now(),
      data
    }
    localStorage.setItem(`draft:${key}`, JSON.stringify(payload))
  } catch (error) {
    console.error("Error saving draft to localStorage:", error)
  }
}

export const loadDraft = (key: string, expiryMs: number = 86400000): any | null => {
  try {
    const raw = localStorage.getItem(`draft:${key}`)
    if (!raw) return null
    
    const parsed = JSON.parse(raw)
    // Check expiry (default: 24 hours)
    if (Date.now() - parsed.timestamp > expiryMs) {
      localStorage.removeItem(`draft:${key}`)
      return null
    }
    return parsed.data
  } catch (error) {
    console.error("Error loading draft from localStorage:", error)
    return null
  }
}

export const clearDraft = (key: string): void => {
  try {
    localStorage.removeItem(`draft:${key}`)
  } catch (error) {
    console.error("Error clearing draft from localStorage:", error)
  }
}
