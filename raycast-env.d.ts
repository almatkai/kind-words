/// <reference types="@raycast/api">

/* 🚧 🚧 🚧
 * This file is auto-generated from the extension's manifest.
 * Do not modify manually. Instead, update the `package.json` file.
 * 🚧 🚧 🚧 */

/* eslint-disable @typescript-eslint/ban-types */

type ExtensionPreferences = {}

/** Preferences accessible in all the extension's commands */
declare type Preferences = ExtensionPreferences

declare namespace Preferences {
  /** Preferences accessible in the `random-compliment` command */
  export type RandomCompliment = ExtensionPreferences & {}
  /** Preferences accessible in the `quick-compliment` command */
  export type QuickCompliment = ExtensionPreferences & {}
  /** Preferences accessible in the `gratitude-note` command */
  export type GratitudeNote = ExtensionPreferences & {}
}

declare namespace Arguments {
  /** Arguments passed to the `random-compliment` command */
  export type RandomCompliment = {}
  /** Arguments passed to the `quick-compliment` command */
  export type QuickCompliment = {}
  /** Arguments passed to the `gratitude-note` command */
  export type GratitudeNote = {}
}

