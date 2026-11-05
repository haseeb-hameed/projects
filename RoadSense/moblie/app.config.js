// Single dynamic app configuration. Secrets are supplied by the environment, not committed.
const base={
  "name": "RoadSense",
  "slug": "roadsense",
  "version": "2.5.1",
  "orientation": "portrait",
  "userInterfaceStyle": "dark",
  "android": {
    "package": "in.edu.roadsense.app",
    "permissions": [
      "ACCESS_FINE_LOCATION",
      "ACCESS_COARSE_LOCATION",
      "CAMERA",
      "POST_NOTIFICATIONS"
    ]
  },
  "plugins": [
    ["expo-image-picker", {"photosPermission":"Choose road photos or short videos to review and attach as evidence.","cameraPermission":false,"microphonePermission":false}],
    "expo-video",
    [
      "expo-location",
      {
        "locationWhenInUsePermission": "Allow RoadSense to show your position on the map."
      }
    ],
    [
      "expo-camera",
      {
        "cameraPermission": "Allow RoadSense to process road frames for hazard detection.",
        "recordAudioAndroid": false
      }
    ],
    "expo-secure-store",
    "expo-notifications",
    [
      "react-native-maps",
      {}
    ]
  ],
  "extra": {
    "note": "Set EXPO_PUBLIC_API_URL in .env to your reachable backend HTTPS URL."
  }
};
module.exports=()=>({
 ...base,
 plugins:base.plugins.map(p=>Array.isArray(p)&&p[0]==='react-native-maps'
  ?['react-native-maps',process.env.GOOGLE_MAPS_API_KEY?{androidGoogleMapsApiKey:process.env.GOOGLE_MAPS_API_KEY}:{}]
  :p),
 extra:{...base.extra,...(process.env.EAS_PROJECT_ID?{eas:{projectId:process.env.EAS_PROJECT_ID}}:{})}
});
