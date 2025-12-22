/**
 * User Preferences Hook
 *
 * Stores and retrieves user preferences from localStorage.
 * Used for default scaffolding settings across the application.
 */

import { useState, useEffect, useCallback } from 'react'

// Preference types
export type FloorHeight = '2.5' | '3.0'
export type ScaffoldingSystem = 'blitz70' | 'allround' | 'combined'
export type WidthClass = 'W06' | 'W09' | 'W12'
export type RoofForm = 'flach' | 'satteldach' | 'walmdach'
export type WorkType = 'dacharbeiten' | 'fassadenarbeiten'
export type ScaffoldType = 'arbeitsgeruest' | 'schutzgeruest' | 'fanggeruest'

export interface UserPreferences {
  // Material preferences
  defaultFloorHeight: FloorHeight

  // Scaffolding system preferences
  defaultSystem: ScaffoldingSystem
  defaultWidthClass: WidthClass

  // Building defaults
  defaultRoofForm: RoofForm

  // Work type defaults
  defaultWorkType: WorkType
  defaultScaffoldType: ScaffoldType

  // Last used values (for convenience)
  lastUsedAddress?: string
}

const STORAGE_KEY = 'geodaten-ch-preferences'

const DEFAULT_PREFERENCES: UserPreferences = {
  defaultFloorHeight: '2.5',        // Lighter floors preferred
  defaultSystem: 'blitz70',          // Blitz for simple facades
  defaultWidthClass: 'W09',          // Standard width
  defaultRoofForm: 'satteldach',     // Gable roof common in CH
  defaultWorkType: 'dacharbeiten',   // Roof work default (+1m SUVA)
  defaultScaffoldType: 'arbeitsgeruest',
}

/**
 * Load preferences from localStorage
 */
function loadPreferences(): UserPreferences {
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (stored) {
      const parsed = JSON.parse(stored)
      // Merge with defaults to handle new preference keys
      return { ...DEFAULT_PREFERENCES, ...parsed }
    }
  } catch (error) {
    console.warn('Failed to load preferences from localStorage:', error)
  }
  return DEFAULT_PREFERENCES
}

/**
 * Save preferences to localStorage
 */
function savePreferences(preferences: UserPreferences): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(preferences))
  } catch (error) {
    console.warn('Failed to save preferences to localStorage:', error)
  }
}

/**
 * Hook for managing user preferences
 *
 * @returns Object with preferences and update functions
 */
export function useUserPreferences() {
  const [preferences, setPreferences] = useState<UserPreferences>(loadPreferences)

  // Save to localStorage whenever preferences change
  useEffect(() => {
    savePreferences(preferences)
  }, [preferences])

  /**
   * Update one or more preferences
   */
  const updatePreferences = useCallback((updates: Partial<UserPreferences>) => {
    setPreferences(prev => ({ ...prev, ...updates }))
  }, [])

  /**
   * Reset all preferences to defaults
   */
  const resetPreferences = useCallback(() => {
    setPreferences(DEFAULT_PREFERENCES)
  }, [])

  /**
   * Update a single preference value
   */
  const setPreference = useCallback(<K extends keyof UserPreferences>(
    key: K,
    value: UserPreferences[K]
  ) => {
    setPreferences(prev => ({ ...prev, [key]: value }))
  }, [])

  return {
    preferences,
    updatePreferences,
    resetPreferences,
    setPreference,
    DEFAULT_PREFERENCES,
  }
}

// Types are already exported above (export interface/type)
