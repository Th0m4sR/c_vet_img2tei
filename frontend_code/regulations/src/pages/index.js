import React from 'react';
// Layout
import RootLayout from '@/app/layout';

export default function Home() {
  return (
    <RootLayout>
      <div className="text-center">
        <h1 className="text-muted">Willkommen zur Website für digitalisierte Ausbildungsordnungen</h1>
        <p>Hier können Ausbildungsordnungen hochgeladen und verarbeitet werden.</p>
        <p>Digitalisierte Verordnungen können hier auch gesucht werden</p>
      </div>
    </RootLayout>
  );
}
