# RoadSense native 2.5.1 — saved DEMO potholes (Expo SDK 58)

Read **../SAVED-POTHOLES-GUIDE.md** first. Mobile-only update after the 2.5 media-report release; backend remains unchanged.

DEMO potholes now persist in phone-local AsyncStorage 2.2.0. Route changes and vehicle resets do not delete them. Coordinates remain fixed; alerts/counts match the new route geometrically, never by reusing the old route fraction. Show all saved DEMO potholes fits the map to all records; hiding the purple layer does not delete it. Individual/all deletion requires confirmation. These are separate from real community reports and are not cloud-synchronized.

```powershell
npm.cmd ci --legacy-peer-deps
npx expo install --check
npx expo start --clear
```

Use Node 22 LTS >=22.13.0 and SDK58-compatible Expo Go. Rebuild custom clients/APKs for AsyncStorage. Preserve mobile/.env; do not clear phone app/Expo Go data. Ordinary reloads keep new saved records; reinstall/clear-data/project-sandbox changes may not. Previously erased or old in-memory-only markers cannot be recovered/migrated by this update.

Validated: clean install, dependencies aligned, Expo Doctor 20/20, 25 native helper/storage/mocked UI tests, Android export 766 modules / 2.2 MB. Native phone disk/lifecycle has not been tested here. No backend/browser tests rerun for this mobile-only change. Audit: 3 high / 5 low. See ../docs/SAVED-DEMO-VALIDATION.txt and ../docs/SAVED-DEMO-AUDIT.json.
