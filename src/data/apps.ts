// One entry per app. Each entry generates /apps/<slug>/, /apps/<slug>/support/ and /apps/<slug>/privacy/.
// appStoreId stays null until App Store Connect assigns one; the badge then renders as "Coming soon".
export interface AppFaq { q: string; a: string }
export interface AppEntry {
  slug: string;
  name: string;
  tagline: string;
  summary: string;
  status: 'coming-soon' | 'beta' | 'available';
  appStoreId: string | null;
  accent: string; // placeholder accent; marketing replaces via tokens
  requirements: string;
  features: { title: string; body: string }[];
  faq: AppFaq[];
  privacy: {
    collected: string[];
    onDevice: string[];
    thirdParties: string[];
    retention: string;
  };
}

export const APPS: AppEntry[] = [
  {
    slug: 'roommeasure',
    name: 'RoomMeasure',
    tagline: 'Measure a room in the time it takes to walk around it.',
    summary:
      'RoomMeasure uses your iPhone’s LiDAR scanner to capture walls, doors and windows and turn them into accurate dimensions and a clean floor plan.',
    status: 'beta',
    appStoreId: null,
    accent: '#3d6fb6',
    requirements: 'iPhone with LiDAR (iPhone 15 Pro or later recommended). Latest iOS.',
    features: [
      { title: 'Walk-around scanning', body: 'Point and walk. Walls, openings and ceiling height are captured as you go.' },
      { title: 'Floor plans you can share', body: 'Export dimensions and a tidy plan to send to a contractor or keep for later.' },
      { title: 'Works on device', body: 'Scans are processed on your iPhone. No account is needed to measure.' },
    ],
    faq: [
      { q: 'Which iPhones are supported?', a: 'iPhones with a LiDAR scanner. Pro models from iPhone 15 Pro onward give the best results.' },
      { q: 'How accurate is it?', a: 'Typical results are within a few centimetres for wall lengths in a well-lit room. Always confirm critical measurements.' },
      { q: 'Do my scans leave my phone?', a: 'Not unless you export or share them yourself.' },
    ],
    privacy: {
      collected: ['Crash and performance diagnostics, if you opt in through iOS settings.'],
      onDevice: ['Camera and LiDAR data used to build room scans.', 'Saved scans and floor plans.'],
      thirdParties: ['Apple (TestFlight / App Store analytics as configured in iOS).'],
      retention: 'Scans stay on your device until you delete them or delete the app.',
    },
  },
  {
    slug: 'tendril',
    name: 'Tendril',
    tagline: 'Know your plants. Keep them thriving.',
    summary:
      'Tendril recognises your houseplants from a photo and turns care into simple, timely reminders for light, water and feeding.',
    status: 'coming-soon',
    appStoreId: null,
    accent: '#3f8a5a',
    requirements: 'iPhone 15 or later. Latest iOS. LiDAR not required.',
    features: [
      { title: 'Snap to identify', body: 'Point your camera at a plant to recognise it, right on your phone.' },
      { title: 'Care that fits your home', body: 'Reminders adapt to the season and to where each plant lives.' },
      { title: 'Your plants, your device', body: 'Recognition runs on device; photos are not uploaded to identify a plant.' },
    ],
    faq: [
      { q: 'Does Tendril work offline?', a: 'Plant recognition runs on your iPhone, so it works without a connection.' },
      { q: 'Which plants does it know?', a: 'Common houseplants first, with more species added in updates.' },
      { q: 'Will it remind me to water?', a: 'Yes. You choose how and when reminders arrive.' },
    ],
    privacy: {
      collected: ['Crash and performance diagnostics, if you opt in through iOS settings.'],
      onDevice: ['Plant photos used for recognition.', 'Your plant list and care schedule.'],
      thirdParties: ['Apple (App Store analytics as configured in iOS).'],
      retention: 'Your plant data stays on your device until you delete it or delete the app.',
    },
  },
  {
    slug: 'gear-bins',
    name: 'Gear Bins',
    tagline: 'Know what’s in every drawer, bin and box.',
    summary:
      'Gear Bins catalogues tools and household items with your camera, so you can find the right bin without opening every one.',
    status: 'coming-soon',
    appStoreId: null,
    accent: '#b5762c',
    requirements: 'iPhone 15 Pro or later recommended. Latest iOS.',
    features: [
      { title: 'Scan a drawer', body: 'Take a photo; Gear Bins recognises tools and everyday items and files them by bin.' },
      { title: 'Search everything', body: 'Type “tape measure” and see exactly which bin it is in.' },
      { title: 'Private by design', body: 'Recognition runs on your iPhone; your catalogue stays yours.' },
    ],
    faq: [
      { q: 'What kinds of items does it recognise?', a: 'Common hand tools, hardware and household items, with more added over time.' },
      { q: 'Can I add items it does not know?', a: 'Yes. Name an item once and Gear Bins learns to match it in your bins.' },
      { q: 'Is my catalogue uploaded?', a: 'No. Your catalogue is stored on your device.' },
    ],
    privacy: {
      collected: ['Crash and performance diagnostics, if you opt in through iOS settings.'],
      onDevice: ['Photos of drawers and bins used for recognition.', 'Your item catalogue.'],
      thirdParties: ['Apple (App Store analytics as configured in iOS).'],
      retention: 'Your catalogue stays on your device until you delete it or delete the app.',
    },
  },
];

export const appBySlug = (slug: string) => APPS.find((a) => a.slug === slug);
