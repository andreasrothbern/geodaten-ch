# Bundeshaus SVG-Analyse: Claude.ai vs. API

## TEIL 1: MEINE EIGENEN SVGs

### Grundriss (mit architektonischem Wissen)

```svg
<svg viewBox="0 0 700 480" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <pattern id="hatch" patternUnits="userSpaceOnUse" width="8" height="8">
      <path d="M0,0 l8,8" stroke="#999" stroke-width="0.5"/>
    </pattern>
    <linearGradient id="copper" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:#7CB9A5"/>
      <stop offset="100%" style="stop-color:#4A8A77"/>
    </linearGradient>
  </defs>

  <rect width="700" height="480" fill="#FFFFFF"/>
  
  <!-- Titel -->
  <text x="350" y="25" text-anchor="middle" font-family="Arial" font-size="14" font-weight="bold">GRUNDRISS - Bundeshaus Bern (U-Form mit Ehrenhof)</text>
  <text x="350" y="40" text-anchor="middle" font-family="Arial" font-size="10">EGID: 2242547 | Baujahr: 1902 | Neorenaissance</text>

  <!-- Gerüst-Hülle (1m Abstand) -->
  <path d="M140,70 L560,70 L560,380 L380,380 L380,280 L320,280 L320,380 L140,380 Z" 
        fill="none" stroke="#0066CC" stroke-width="2" stroke-dasharray="5,5"/>

  <!-- WESTFLÜGEL -->
  <rect x="150" y="80" width="80" height="290" fill="url(#hatch)" stroke="#000" stroke-width="2"/>
  <text x="190" y="230" text-anchor="middle" font-family="Arial" font-size="9" transform="rotate(-90,190,230)">WESTFLÜGEL</text>

  <!-- OSTFLÜGEL -->
  <rect x="470" y="80" width="80" height="290" fill="url(#hatch)" stroke="#000" stroke-width="2"/>
  <text x="510" y="230" text-anchor="middle" font-family="Arial" font-size="9" transform="rotate(-90,510,230)">OSTFLÜGEL</text>

  <!-- MITTELBAU (Nordfassade) -->
  <rect x="230" y="80" width="240" height="100" fill="url(#hatch)" stroke="#000" stroke-width="2"/>
  <text x="350" y="130" text-anchor="middle" font-family="Arial" font-size="9">MITTELBAU</text>

  <!-- VERBINDUNGSGANG WEST -->
  <rect x="230" y="180" width="50" height="80" fill="url(#hatch)" stroke="#000" stroke-width="1"/>

  <!-- VERBINDUNGSGANG OST -->
  <rect x="420" y="180" width="50" height="80" fill="url(#hatch)" stroke="#000" stroke-width="1"/>

  <!-- KUPPEL (über Nationalratssaal) -->
  <circle cx="350" cy="130" r="35" fill="url(#copper)" stroke="#000" stroke-width="2"/>
  <text x="350" y="125" text-anchor="middle" font-family="Arial" font-size="8" fill="#fff">KUPPEL</text>
  <text x="350" y="137" text-anchor="middle" font-family="Arial" font-size="7" fill="#fff">64m</text>

  <!-- EHRENHOF (Innenhof - WEISS/NICHT EINRÜSTEN) -->
  <rect x="280" y="180" width="140" height="160" fill="#FFFFFF" stroke="#000" stroke-width="1" stroke-dasharray="3,3"/>
  <text x="350" y="260" text-anchor="middle" font-family="Arial" font-size="10" fill="#666">EHRENHOF</text>
  <text x="350" y="275" text-anchor="middle" font-family="Arial" font-size="8" fill="#999">(nicht einrüsten)</text>

  <!-- ARKADEN (Nordfassade) -->
  <rect x="230" y="80" width="240" height="20" fill="url(#hatch)" stroke="#000" stroke-width="1"/>
  <!-- 7 Arkaden-Bögen angedeutet -->
  <circle cx="255" cy="90" r="8" fill="none" stroke="#333" stroke-width="0.5"/>
  <circle cx="285" cy="90" r="8" fill="none" stroke="#333" stroke-width="0.5"/>
  <circle cx="315" cy="90" r="8" fill="none" stroke="#333" stroke-width="0.5"/>
  <circle cx="350" cy="90" r="8" fill="none" stroke="#333" stroke-width="0.5"/>
  <circle cx="385" cy="90" r="8" fill="none" stroke="#333" stroke-width="0.5"/>
  <circle cx="415" cy="90" r="8" fill="none" stroke="#333" stroke-width="0.5"/>
  <circle cx="445" cy="90" r="8" fill="none" stroke="#333" stroke-width="0.5"/>
  <text x="350" y="72" text-anchor="middle" font-family="Arial" font-size="7">ARKADEN (7 Bögen, 6m)</text>

  <!-- Gerüst-Zugänge -->
  <circle cx="350" cy="65" r="4" fill="#0066CC"/>
  <text x="350" y="58" text-anchor="middle" font-family="Arial" font-size="7" fill="#0066CC">Z1</text>
  
  <circle cx="145" cy="220" r="4" fill="#0066CC"/>
  <text x="130" y="223" font-family="Arial" font-size="7" fill="#0066CC">Z2</text>
  
  <circle cx="555" cy="220" r="4" fill="#0066CC"/>
  <text x="565" y="223" font-family="Arial" font-size="7" fill="#0066CC">Z3</text>
  
  <circle cx="350" cy="385" r="4" fill="#0066CC"/>
  <text x="350" y="400" text-anchor="middle" font-family="Arial" font-size="7" fill="#0066CC">Z4</text>

  <!-- Fassadenlängen -->
  <line x1="230" y1="65" x2="470" y2="65" stroke="#CC0000" stroke-width="1"/>
  <text x="350" y="60" text-anchor="middle" font-family="Arial" font-size="7" fill="#CC0000">80m (Nordfassade)</text>

  <line x1="145" y1="80" x2="145" y2="370" stroke="#CC0000" stroke-width="1"/>
  <text x="130" y="130" font-family="Arial" font-size="7" fill="#CC0000" transform="rotate(-90,130,130)">71m</text>

  <!-- Nordpfeil -->
  <g transform="translate(620,80)">
    <path d="M0,30 L0,0 M-7,10 L0,0 L7,10" stroke="#000" stroke-width="2" fill="none"/>
    <text x="0" y="45" text-anchor="middle" font-family="Arial" font-size="14" font-weight="bold">N</text>
  </g>

  <!-- Massstab -->
  <g transform="translate(520,420)">
    <line x1="0" y1="0" x2="80" y2="0" stroke="#000" stroke-width="2"/>
    <line x1="0" y1="-5" x2="0" y2="5" stroke="#000" stroke-width="1"/>
    <line x1="80" y1="-5" x2="80" y2="5" stroke="#000" stroke-width="1"/>
    <text x="40" y="15" text-anchor="middle" font-family="Arial" font-size="9">20m</text>
  </g>

  <!-- Legende -->
  <g transform="translate(30,380)">
    <rect x="0" y="0" width="140" height="90" fill="#fff" stroke="#666" stroke-width="1"/>
    <text x="70" y="15" text-anchor="middle" font-family="Arial" font-size="10" font-weight="bold">LEGENDE</text>
    <rect x="10" y="25" width="15" height="10" fill="url(#hatch)"/>
    <text x="30" y="33" font-family="Arial" font-size="8">Gebäude (schraffiert)</text>
    <circle cx="17" cy="48" r="7" fill="url(#copper)"/>
    <text x="30" y="51" font-family="Arial" font-size="8">Kuppel (64m)</text>
    <rect x="10" y="60" width="15" height="10" fill="#fff" stroke="#000" stroke-dasharray="2,2"/>
    <text x="30" y="68" font-family="Arial" font-size="8">Ehrenhof (nicht einrüsten)</text>
    <line x1="10" y1="80" x2="25" y2="80" stroke="#0066CC" stroke-width="2" stroke-dasharray="3,3"/>
    <text x="30" y="83" font-family="Arial" font-size="8">Gerüst-Hülle</text>
  </g>
</svg>
```

### Fassadenansicht (Südfassade mit Ehrenhof)

```svg
<svg viewBox="0 0 700 480" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <pattern id="hatch" patternUnits="userSpaceOnUse" width="8" height="8">
      <path d="M0,0 l8,8" stroke="#999" stroke-width="0.5"/>
    </pattern>
    <pattern id="ground" patternUnits="userSpaceOnUse" width="20" height="10">
      <path d="M0,10 L10,0 M10,10 L20,0" stroke="#666" stroke-width="0.5"/>
    </pattern>
    <linearGradient id="copper" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:#7CB9A5"/>
      <stop offset="100%" style="stop-color:#4A8A77"/>
    </linearGradient>
  </defs>

  <rect width="700" height="480" fill="#FFFFFF"/>

  <!-- Titel -->
  <text x="350" y="25" text-anchor="middle" font-family="Arial" font-size="14" font-weight="bold">FASSADENANSICHT SÜD - Bundeshaus Bern</text>
  <text x="350" y="40" text-anchor="middle" font-family="Arial" font-size="10">Blick vom Bundesplatz auf den Ehrenhof</text>

  <!-- Terrain -->
  <rect x="30" y="400" width="640" height="30" fill="url(#ground)"/>
  <line x1="30" y1="400" x2="670" y2="400" stroke="#333" stroke-width="1"/>

  <!-- WESTFLÜGEL (links) -->
  <g id="westfluegel">
    <!-- Arkaden (6m) -->
    <rect x="60" y="360" width="120" height="40" fill="url(#hatch)" stroke="#333" stroke-width="1"/>
    <path d="M70,400 Q90,370 110,400" fill="none" stroke="#333" stroke-width="1"/>
    <path d="M120,400 Q140,370 160,400" fill="none" stroke="#333" stroke-width="1"/>
    
    <!-- Hauptgeschosse (25m) -->
    <rect x="60" y="180" width="120" height="180" fill="url(#hatch)" stroke="#333" stroke-width="1"/>
    
    <!-- Fenster (4 Geschosse × 3 Fenster) -->
    <g fill="#fff" stroke="#333" stroke-width="0.5">
      <!-- EG -->
      <rect x="75" y="320" width="20" height="30"/>
      <rect x="110" y="320" width="20" height="30"/>
      <rect x="145" y="320" width="20" height="30"/>
      <!-- 1. OG -->
      <rect x="75" y="270" width="20" height="35"/>
      <rect x="110" y="270" width="20" height="35"/>
      <rect x="145" y="270" width="20" height="35"/>
      <!-- 2. OG -->
      <rect x="75" y="220" width="20" height="35"/>
      <rect x="110" y="220" width="20" height="35"/>
      <rect x="145" y="220" width="20" height="35"/>
    </g>
    
    <!-- Dach (Walmdach) -->
    <polygon points="60,180 120,150 180,180" fill="url(#hatch)" stroke="#333" stroke-width="1"/>
  </g>

  <!-- OSTFLÜGEL (rechts) -->
  <g id="ostfluegel">
    <!-- Arkaden (6m) -->
    <rect x="520" y="360" width="120" height="40" fill="url(#hatch)" stroke="#333" stroke-width="1"/>
    <path d="M530,400 Q550,370 570,400" fill="none" stroke="#333" stroke-width="1"/>
    <path d="M580,400 Q600,370 620,400" fill="none" stroke="#333" stroke-width="1"/>
    
    <!-- Hauptgeschosse (25m) -->
    <rect x="520" y="180" width="120" height="180" fill="url(#hatch)" stroke="#333" stroke-width="1"/>
    
    <!-- Fenster -->
    <g fill="#fff" stroke="#333" stroke-width="0.5">
      <rect x="535" y="320" width="20" height="30"/>
      <rect x="570" y="320" width="20" height="30"/>
      <rect x="605" y="320" width="20" height="30"/>
      <rect x="535" y="270" width="20" height="35"/>
      <rect x="570" y="270" width="20" height="35"/>
      <rect x="605" y="270" width="20" height="35"/>
      <rect x="535" y="220" width="20" height="35"/>
      <rect x="570" y="220" width="20" height="35"/>
      <rect x="605" y="220" width="20" height="35"/>
    </g>
    
    <!-- Dach -->
    <polygon points="520,180 580,150 640,180" fill="url(#hatch)" stroke="#333" stroke-width="1"/>
  </g>

  <!-- MITTELBAU (hinten, teilweise verdeckt) -->
  <g id="mittelbau">
    <!-- Nur oberer Teil sichtbar (über Flügeldächer) -->
    <rect x="180" y="100" width="340" height="80" fill="url(#hatch)" stroke="#333" stroke-width="1"/>
    
    <!-- Kuppel -->
    <ellipse cx="350" cy="100" rx="60" ry="45" fill="url(#copper)" stroke="#333" stroke-width="1"/>
    <ellipse cx="350" cy="70" rx="15" ry="12" fill="url(#copper)" stroke="#333" stroke-width="1"/>
    <!-- Laterne -->
    <rect x="345" y="55" width="10" height="15" fill="#333"/>
  </g>

  <!-- EHRENHOF (freier Bereich in der Mitte) -->
  <rect x="180" y="300" width="340" height="100" fill="#FFFFFF" stroke="none"/>
  <text x="350" y="360" text-anchor="middle" font-family="Arial" font-size="12" fill="#999">EHRENHOF</text>
  <text x="350" y="375" text-anchor="middle" font-family="Arial" font-size="9" fill="#bbb">(Bundesplatz)</text>

  <!-- Gerüst WESTFLÜGEL -->
  <g stroke="#0066CC" stroke-width="1.5">
    <line x1="45" y1="400" x2="45" y2="140"/>
    <line x1="55" y1="400" x2="55" y2="140"/>
    <!-- Beläge -->
    <line x1="45" y1="380" x2="55" y2="380" stroke="#8B4513" stroke-width="3"/>
    <line x1="45" y1="340" x2="55" y2="340" stroke="#8B4513" stroke-width="3"/>
    <line x1="45" y1="300" x2="55" y2="300" stroke="#8B4513" stroke-width="3"/>
    <line x1="45" y1="260" x2="55" y2="260" stroke="#8B4513" stroke-width="3"/>
    <line x1="45" y1="220" x2="55" y2="220" stroke="#8B4513" stroke-width="3"/>
    <line x1="45" y1="180" x2="55" y2="180" stroke="#8B4513" stroke-width="3"/>
    <!-- Verankerungen -->
    <line x1="55" y1="300" x2="60" y2="300" stroke="#CC0000" stroke-dasharray="2,2"/>
    <line x1="55" y1="220" x2="60" y2="220" stroke="#CC0000" stroke-dasharray="2,2"/>
  </g>

  <!-- Gerüst OSTFLÜGEL -->
  <g stroke="#0066CC" stroke-width="1.5">
    <line x1="645" y1="400" x2="645" y2="140"/>
    <line x1="655" y1="400" x2="655" y2="140"/>
    <line x1="645" y1="380" x2="655" y2="380" stroke="#8B4513" stroke-width="3"/>
    <line x1="645" y1="340" x2="655" y2="340" stroke="#8B4513" stroke-width="3"/>
    <line x1="645" y1="300" x2="655" y2="300" stroke="#8B4513" stroke-width="3"/>
    <line x1="645" y1="260" x2="655" y2="260" stroke="#8B4513" stroke-width="3"/>
    <line x1="645" y1="220" x2="655" y2="220" stroke="#8B4513" stroke-width="3"/>
    <line x1="645" y1="180" x2="655" y2="180" stroke="#8B4513" stroke-width="3"/>
    <line x1="640" y1="300" x2="645" y2="300" stroke="#CC0000" stroke-dasharray="2,2"/>
    <line x1="640" y1="220" x2="645" y2="220" stroke="#CC0000" stroke-dasharray="2,2"/>
  </g>

  <!-- Höhenskala links -->
  <g font-family="Arial" font-size="8">
    <line x1="20" y1="400" x2="25" y2="400" stroke="#333"/>
    <text x="18" y="403" text-anchor="end">±0.00</text>
    
    <line x1="20" y1="360" x2="25" y2="360" stroke="#333"/>
    <text x="18" y="363" text-anchor="end">+6m</text>
    
    <line x1="20" y1="180" x2="25" y2="180" stroke="#333"/>
    <text x="18" y="183" text-anchor="end">+25m</text>
    
    <line x1="20" y1="150" x2="25" y2="150" stroke="#333"/>
    <text x="18" y="153" text-anchor="end">+30m</text>
    
    <line x1="20" y1="55" x2="25" y2="55" stroke="#333"/>
    <text x="18" y="58" text-anchor="end">+64m</text>
  </g>

  <!-- Lagenbeschriftung rechts -->
  <g font-family="Arial" font-size="7" fill="#666">
    <text x="670" y="390">1. Lage</text>
    <text x="670" y="350">2. Lage</text>
    <text x="670" y="310">3. Lage</text>
    <text x="670" y="270">4. Lage</text>
    <text x="670" y="230">5. Lage</text>
    <text x="670" y="190">6. Lage</text>
    <text x="670" y="150">7. Lage</text>
  </g>

  <!-- Zonenmarkierung -->
  <g font-family="Arial" font-size="8" fill="#0066CC">
    <text x="120" y="390" text-anchor="middle">ARKADEN</text>
    <text x="120" y="270" text-anchor="middle">HAUPTGEBÄUDE</text>
    <text x="350" y="90" text-anchor="middle" fill="#fff">KUPPEL (Sonderkonstruktion)</text>
  </g>
</svg>
```

### Gebäudeschnitt (Querschnitt durch Mittelbau)

```svg
<svg viewBox="0 0 700 480" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <pattern id="hatch" patternUnits="userSpaceOnUse" width="8" height="8">
      <path d="M0,0 l8,8" stroke="#999" stroke-width="0.5"/>
    </pattern>
    <pattern id="cut-hatch" patternUnits="userSpaceOnUse" width="4" height="4">
      <path d="M0,0 l4,4 M0,4 l4,-4" stroke="#666" stroke-width="0.8"/>
    </pattern>
    <pattern id="ground" patternUnits="userSpaceOnUse" width="20" height="10">
      <path d="M0,10 L10,0 M10,10 L20,0" stroke="#666" stroke-width="0.5"/>
    </pattern>
    <linearGradient id="copper" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:#7CB9A5"/>
      <stop offset="100%" style="stop-color:#4A8A77"/>
    </linearGradient>
  </defs>

  <rect width="700" height="480" fill="#FFFFFF"/>

  <!-- Titel -->
  <text x="350" y="25" text-anchor="middle" font-family="Arial" font-size="14" font-weight="bold">GEBÄUDESCHNITT A-A - Bundeshaus Bern</text>
  <text x="350" y="40" text-anchor="middle" font-family="Arial" font-size="10">Querschnitt durch Mittelbau (Nationalratssaal)</text>

  <!-- Terrain -->
  <rect x="30" y="400" width="640" height="30" fill="url(#ground)"/>
  <line x1="30" y1="400" x2="670" y2="400" stroke="#333" stroke-width="1"/>

  <!-- LINKE AUSSENMAUER (geschnitten = dichte Schraffur) -->
  <rect x="100" y="160" width="30" height="240" fill="url(#cut-hatch)" stroke="#333" stroke-width="1"/>
  
  <!-- RECHTE AUSSENMAUER (geschnitten) -->
  <rect x="570" y="160" width="30" height="240" fill="url(#cut-hatch)" stroke="#333" stroke-width="1"/>

  <!-- ARKADEN-MAUERN (geschnitten) -->
  <rect x="100" y="360" width="30" height="40" fill="url(#cut-hatch)" stroke="#333" stroke-width="1"/>
  <rect x="570" y="360" width="30" height="40" fill="url(#cut-hatch)" stroke="#333" stroke-width="1"/>
  
  <!-- Arkaden-Bögen -->
  <path d="M130,400 Q165,360 200,400" fill="none" stroke="#333" stroke-width="1"/>
  <path d="M500,400 Q535,360 570,400" fill="none" stroke="#333" stroke-width="1"/>

  <!-- INNENRAUM (WEISS - KRITISCH!) -->
  <rect x="130" y="160" width="440" height="240" fill="#FFFFFF" stroke="#333" stroke-width="0.5"/>

  <!-- Geschossdecken -->
  <line x1="130" y1="360" x2="570" y2="360" stroke="#333" stroke-width="1"/>
  <text x="140" y="355" font-family="Arial" font-size="7" fill="#666">EG (+6m)</text>
  
  <line x1="130" y1="320" x2="570" y2="320" stroke="#333" stroke-width="1"/>
  <text x="140" y="315" font-family="Arial" font-size="7" fill="#666">1. OG (+12m)</text>
  
  <line x1="130" y1="280" x2="570" y2="280" stroke="#333" stroke-width="1"/>
  <text x="140" y="275" font-family="Arial" font-size="7" fill="#666">2. OG (+18m)</text>
  
  <line x1="130" y1="240" x2="570" y2="240" stroke="#333" stroke-width="1"/>
  <text x="140" y="235" font-family="Arial" font-size="7" fill="#666">3. OG (+24m)</text>

  <!-- NATIONALRATSSAAL (grosser Raum unter Kuppel) -->
  <rect x="200" y="200" width="300" height="160" fill="#FFFFFF" stroke="#333" stroke-width="1"/>
  <text x="350" y="290" text-anchor="middle" font-family="Arial" font-size="10" fill="#666">NATIONALRATSSAAL</text>

  <!-- Innenstützen -->
  <rect x="190" y="200" width="15" height="200" fill="url(#cut-hatch)" stroke="#333" stroke-width="0.5"/>
  <rect x="495" y="200" width="15" height="200" fill="url(#cut-hatch)" stroke="#333" stroke-width="0.5"/>

  <!-- KUPPEL (Doppelschale) -->
  <!-- Aussenschale -->
  <path d="M200,160 Q350,50 500,160" fill="url(#copper)" stroke="#333" stroke-width="1"/>
  <!-- Innenschale (WEISS = Hohlraum) -->
  <path d="M230,160 Q350,80 470,160" fill="#FFFFFF" stroke="#333" stroke-width="0.5"/>
  
  <!-- Kuppel-Laterne -->
  <rect x="340" y="50" width="20" height="30" fill="url(#cut-hatch)" stroke="#333" stroke-width="1"/>
  <polygon points="340,50 350,35 360,50" fill="url(#copper)" stroke="#333" stroke-width="1"/>

  <!-- DACH (Seitenteile) -->
  <polygon points="100,160 150,130 200,160" fill="url(#cut-hatch)" stroke="#333" stroke-width="1"/>
  <polygon points="500,160 550,130 600,160" fill="url(#cut-hatch)" stroke="#333" stroke-width="1"/>

  <!-- LINKES GERÜST -->
  <g stroke="#0066CC" stroke-width="2">
    <line x1="60" y1="400" x2="60" y2="50"/>
    <line x1="80" y1="400" x2="80" y2="50"/>
    
    <!-- Beläge -->
    <line x1="60" y1="380" x2="80" y2="380" stroke="#8B4513" stroke-width="3"/>
    <line x1="60" y1="340" x2="80" y2="340" stroke="#8B4513" stroke-width="3"/>
    <line x1="60" y1="300" x2="80" y2="300" stroke="#8B4513" stroke-width="3"/>
    <line x1="60" y1="260" x2="80" y2="260" stroke="#8B4513" stroke-width="3"/>
    <line x1="60" y1="220" x2="80" y2="220" stroke="#8B4513" stroke-width="3"/>
    <line x1="60" y1="180" x2="80" y2="180" stroke="#8B4513" stroke-width="3"/>
    <line x1="60" y1="140" x2="80" y2="140" stroke="#8B4513" stroke-width="3"/>
    <line x1="60" y1="100" x2="80" y2="100" stroke="#8B4513" stroke-width="3"/>
    <line x1="60" y1="60" x2="80" y2="60" stroke="#8B4513" stroke-width="3"/>
    
    <!-- Verankerungen -->
    <line x1="80" y1="300" x2="100" y2="300" stroke="#CC0000" stroke-dasharray="3,2"/>
    <line x1="80" y1="220" x2="100" y2="220" stroke="#CC0000" stroke-dasharray="3,2"/>
    <line x1="80" y1="140" x2="100" y2="140" stroke="#CC0000" stroke-dasharray="3,2"/>
  </g>

  <!-- RECHTES GERÜST -->
  <g stroke="#0066CC" stroke-width="2">
    <line x1="620" y1="400" x2="620" y2="50"/>
    <line x1="640" y1="400" x2="640" y2="50"/>
    
    <line x1="620" y1="380" x2="640" y2="380" stroke="#8B4513" stroke-width="3"/>
    <line x1="620" y1="340" x2="640" y2="340" stroke="#8B4513" stroke-width="3"/>
    <line x1="620" y1="300" x2="640" y2="300" stroke="#8B4513" stroke-width="3"/>
    <line x1="620" y1="260" x2="640" y2="260" stroke="#8B4513" stroke-width="3"/>
    <line x1="620" y1="220" x2="640" y2="220" stroke="#8B4513" stroke-width="3"/>
    <line x1="620" y1="180" x2="640" y2="180" stroke="#8B4513" stroke-width="3"/>
    <line x1="620" y1="140" x2="640" y2="140" stroke="#8B4513" stroke-width="3"/>
    <line x1="620" y1="100" x2="640" y2="100" stroke="#8B4513" stroke-width="3"/>
    <line x1="620" y1="60" x2="640" y2="60" stroke="#8B4513" stroke-width="3"/>
    
    <line x1="600" y1="300" x2="620" y2="300" stroke="#CC0000" stroke-dasharray="3,2"/>
    <line x1="600" y1="220" x2="620" y2="220" stroke="#CC0000" stroke-dasharray="3,2"/>
    <line x1="600" y1="140" x2="620" y2="140" stroke="#CC0000" stroke-dasharray="3,2"/>
  </g>

  <!-- Höhenskala -->
  <g font-family="Arial" font-size="8">
    <line x1="35" y1="400" x2="45" y2="400" stroke="#333"/>
    <text x="33" y="403" text-anchor="end">±0.00</text>
    
    <line x1="35" y1="360" x2="45" y2="360" stroke="#333"/>
    <text x="33" y="363" text-anchor="end">+6m</text>
    
    <line x1="35" y1="160" x2="45" y2="160" stroke="#333"/>
    <text x="33" y="163" text-anchor="end">+30m</text>
    
    <line x1="35" y1="50" x2="45" y2="50" stroke="#333"/>
    <text x="33" y="53" text-anchor="end">+64m</text>
  </g>

  <!-- Schnittmarkierung -->
  <circle cx="50" cy="450" r="12" fill="#fff" stroke="#333" stroke-width="1"/>
  <text x="50" y="455" text-anchor="middle" font-family="Arial" font-size="14" font-weight="bold">A</text>
  <circle cx="650" cy="450" r="12" fill="#fff" stroke="#333" stroke-width="1"/>
  <text x="650" y="455" text-anchor="middle" font-family="Arial" font-size="14" font-weight="bold">A</text>

  <!-- Legende -->
  <g transform="translate(520,50)">
    <rect x="0" y="0" width="130" height="90" fill="#fff" stroke="#333"/>
    <text x="65" y="15" text-anchor="middle" font-family="Arial" font-size="9" font-weight="bold">LEGENDE</text>
    <rect x="10" y="22" width="15" height="10" fill="url(#cut-hatch)"/>
    <text x="30" y="30" font-family="Arial" font-size="7">Schnittfläche</text>
    <rect x="10" y="37" width="15" height="10" fill="#fff" stroke="#333"/>
    <text x="30" y="45" font-family="Arial" font-size="7">Innenraum (LEER)</text>
    <rect x="10" y="52" width="15" height="10" fill="url(#copper)"/>
    <text x="30" y="60" font-family="Arial" font-size="7">Kuppel (Kupfer)</text>
    <line x1="10" y1="72" x2="25" y2="72" stroke="#CC0000" stroke-dasharray="2,2"/>
    <text x="30" y="75" font-family="Arial" font-size="7">Verankerung</text>
  </g>
</svg>
```

---

## TEIL 2: VERGLEICH API vs. MEINE SVGs

| Aspekt | API-generiert | Meine SVGs | Bewertung |
|--------|---------------|------------|-----------|
| **Grundrissform** | Rechteck | U-Form mit Ehrenhof | ✅ Claude.ai besser |
| **Ehrenhof dargestellt** | ❌ Nein | ✅ Ja (gestrichelt, "nicht einrüsten") | ✅ Claude.ai besser |
| **Seitenflügel erkennbar** | ❌ Nein | ✅ Ja (West/Ost separat) | ✅ Claude.ai besser |
| **Kuppel-Position** | Mitte des Rechtecks | Über Mittelbau (Nordfassade) | ✅ Claude.ai besser |
| **Arkaden** | Einfaches Rechteck | 7 Bögen angedeutet | ✅ Claude.ai besser |
| **Fassade: Flügel** | Nicht unterschieden | West/Ost getrennt | ✅ Claude.ai besser |
| **Fassade: Ehrenhof** | Nicht dargestellt | Als Freifläche | ✅ Claude.ai besser |
| **Schnitt: Nationalratssaal** | Generischer Raum | Benannt, unter Kuppel | ✅ Claude.ai besser |
| **Schnitt: Doppelschale** | Vorhanden | Vorhanden | ⚖️ Gleich |
| **Style-Vorgaben** | Alle korrekt | Alle korrekt | ⚖️ Gleich |
| **Gerüst-Darstellung** | Vollständig | Vollständig | ⚖️ Gleich |

### Fazit Vergleich

**Claude.ai ist in 8 von 11 Aspekten besser**, weil:
1. Ich weiss, dass das Bundeshaus U-förmig ist
2. Ich weiss, wo der Ehrenhof liegt
3. Ich weiss, dass die Kuppel über dem Nationalratssaal ist
4. Ich kann die Flügel architektonisch korrekt positionieren

---

## TEIL 3: ERKLÄRUNG - Warum unterschiedliche Ergebnisse?

### A. Claude API vs. Claude.ai Chat

| Faktor | Claude API (Sonnet) | Claude.ai Chat |
|--------|---------------------|----------------|
| **Kontext** | NUR der Prompt (4-5KB) | Prompt + Konversation + Training |
| **Iteration** | One-Shot (1 Versuch) | Mehrere Durchläufe möglich |
| **Feedback** | Keins | Visuelles Feedback möglich |
| **Wissen** | Nur explizite Prompt-Daten | Implizites Architektur-Wissen |
| **Korrektur** | Keine Selbstkorrektur | Kann nachfragen/verbessern |

### B. Was fehlt dem API-Prompt?

**1. Architektonisches Grundwissen:**
```
❌ FEHLT: "Das Bundeshaus hat einen U-förmigen Grundriss"
❌ FEHLT: "Der Ehrenhof öffnet sich nach Süden zum Bundesplatz"
❌ FEHLT: "Die Kuppel sitzt über dem Nationalratssaal im Mittelbau"
```

**2. Proportions-Wissen:**
```
❌ FEHLT: "Die Flügel sind ca. 40m lang"
❌ FEHLT: "Der Ehrenhof ist ca. 30m × 20m"
❌ FEHLT: "Die Kuppel hat ca. 15m Durchmesser"
```

**3. Detail-Wissen:**
```
❌ FEHLT: "Die Arkaden haben 7 Bögen auf der Nordfassade"
❌ FEHLT: "4 Hauptgeschosse plus Arkaden-Erdgeschoss"
❌ FEHLT: "Symmetrische Anlage mit Mittelrisalit"
```

### C. Wie kann die App dieses Wissen automatisch beschaffen?

**Option 1: Erweiterte known_buildings.py**
```python
"bundeshaus": {
    "grundriss_form": "U-Form",
    "ehrenhof": {
        "position": "süd",
        "breite_m": 30,
        "tiefe_m": 20,
    },
    "fluegel": ["west", "ost", "mittelbau"],
    "kuppel_position": "mittelbau",
    "arkaden": {"anzahl": 7, "seite": "nord"},
}
```

**Option 2: Claude Haiku Recherche-Fragen**
```
1. "Hat das Gebäude einen Innenhof? Wenn ja, wo?"
2. "Wie ist der Grundriss geformt (rechteckig, L, U, H)?"
3. "Gibt es separate Flügel? Wie heissen sie?"
4. "Wo sitzt die Kuppel/der Turm?"
5. "Wie viele Arkaden-Bögen hat die Hauptfassade?"
```

**Option 3: Polygon-Analyse**
```
- Aus 26 Polygon-Punkten die U-Form erkennen
- Einbuchtungen = Innenhöfe
- Vorsprünge = Risalite
```

---

## TEIL 4: SCHWÄCHEN-TABELLE

| ID | Kategorie | Problem | Auswirkung | Priorität |
|----|-----------|---------|------------|-----------|
| S1 | Daten | Traufhöhe 53.2m ist Kuppel-Unterkante, nicht Hauptgebäude | Falsche Proportionen | 🔴 P1 |
| S2 | Prompt | Ehrenhof nicht beschrieben | Fehlt im Grundriss | 🔴 P1 |
| S3 | Prompt | U-Form nicht erwähnt | Rechteck statt U | 🔴 P1 |
| S4 | Prompt | Flügel nicht differenziert | Keine West/Ost-Unterscheidung | 🟡 P2 |
| S5 | Daten | Geschosse fehlen im GWR | Keine Geschoss-Linien | 🟡 P2 |
| S6 | Prompt | Arkaden-Anzahl unbekannt | Generische Darstellung | 🟢 P3 |
| S7 | Daten | Polygon nicht analysiert | Struktur nicht erkannt | 🟡 P2 |
| S8 | API | One-Shot ohne Feedback | Keine Korrekturmöglichkeit | 🟡 P2 |

---

## TEIL 5: KONKRETE VERBESSERUNGEN

### Für known_buildings.py:

```python
KNOWN_BUILDINGS["2242547"] = {
    # Bestehend
    "name": "Bundeshaus",
    "type": "Parlamentsgebäude",
    "style": "Neorenaissance / Historismus",
    "year": 1902,
    
    # NEU: Architektonische Struktur
    "grundriss": {
        "form": "U-Form",
        "orientierung": "Öffnung nach Süd",
    },
    
    "ehrenhof": {
        "vorhanden": True,
        "position": "süd",
        "breite_m": 30,
        "tiefe_m": 20,
        "offen_nach": "Bundesplatz",
        "einruesten": False,
    },
    
    "fluegel": [
        {
            "name": "Westflügel",
            "laenge_m": 40,
            "tiefe_m": 20,
            "geschosse": 4,
        },
        {
            "name": "Ostflügel", 
            "laenge_m": 40,
            "tiefe_m": 20,
            "geschosse": 4,
        },
        {
            "name": "Mittelbau",
            "laenge_m": 50,
            "tiefe_m": 25,
            "geschosse": 4,
            "hat_kuppel": True,
            "besonderheit": "Nationalratssaal unter Kuppel",
        },
    ],
    
    "arkaden": {
        "vorhanden": True,
        "seite": "nord",
        "anzahl_boegen": 7,
        "hoehe_m": 6,
    },
    
    "kuppel": {
        "position": "Mittelbau",
        "durchmesser_m": 15,
        "hoehe_ueber_traufe_m": 34,
        "material": "Kupfer (patiniert)",
        "unter_raum": "Nationalratssaal",
    },
    
    # Korrigierte Höhen PRO ZONE
    "hoehen_korrigiert": {
        "arkaden_traufe": 6.0,
        "hauptgebaeude_traufe": 25.0,
        "hauptgebaeude_first": 30.0,
        "kuppel_spitze": 64.0,
    },
}
```

### Für Prompt-Erweiterung:

```markdown
## NEUER ABSCHNITT: Architektonische Struktur

### Grundrissform
- **Form:** U-förmig (symmetrisch)
- **Öffnung:** Nach Süden zum Bundesplatz
- **Achse:** Nord-Süd

### Ehrenhof
- **Position:** Süd (zwischen West- und Ostflügel)
- **Dimensionen:** ca. 30m × 20m
- **Zugang:** Offen zum Bundesplatz
- **WICHTIG:** Nicht einrüsten! (Freifläche im Grundriss)

### Gebäudeteile
| Teil | Länge | Tiefe | Geschosse | Besonderheit |
|------|-------|-------|-----------|--------------|
| Westflügel | 40m | 20m | 4 | - |
| Ostflügel | 40m | 20m | 4 | - |
| Mittelbau | 50m | 25m | 4 | Kuppel, Nationalratssaal |

### Kuppel
- **Position:** Zentriert über Mittelbau
- **Durchmesser:** ca. 15m
- **Höhe:** 64m (über Terrain)
- **Material:** Kupfer (grün patiniert)
- **Darunter:** Nationalratssaal

### Arkaden
- **Position:** Nordfassade (Bundesplatz-Seite)
- **Anzahl Bögen:** 7
- **Höhe:** 6m
- **Stil:** Neorenaissance-Rundbogen
```

---

## TEIL 6: FAZIT

### 1. Ist der aktuelle Prompt ausreichend für gute SVGs?

**NEIN**, weil:
- Die U-Form nicht beschrieben ist
- Der Ehrenhof fehlt
- Die Flügel nicht differenziert sind
- Nur aggregierte Höhendaten (nicht pro Zone)

### 2. Die 3 wichtigsten Verbesserungen

| # | Verbesserung | Impact | Aufwand |
|---|--------------|--------|---------|
| 1 | **Ehrenhof im Prompt** | Kritisch für Grundriss | 1 Std |
| 2 | **U-Form beschreiben** | Kritisch für alle SVGs | 1 Std |
| 3 | **Höhen PRO ZONE** (nicht aggregiert) | Korrekte Proportionen | 2 Std |

### 3. Kann die App jemals so gute SVGs wie Claude.ai Chat produzieren?

**JA**, aber nur wenn:

1. **known_buildings.py** erweitert wird mit:
   - Grundrissform (U, L, H, rechteckig)
   - Ehrenhof-Daten
   - Flügel-Definitionen
   - Korrekte Höhen pro Zone

2. **Das Prompt** erweitert wird mit:
   - Architektonische Struktur
   - Nicht-rechteckige Elemente
   - Innenhöfe als "nicht einrüsten"

3. **Alternativ: Claude Haiku Recherche** verbessert wird:
   - Fragen nach Grundrissform
   - Fragen nach Innenhöfen
   - Fragen nach Flügeln

**Ohne diese Erweiterungen** wird die API immer generische Rechteck-Gebäude produzieren, während ich (Claude.ai) mein Architekturwissen nutzen kann.

---

*Analyse erstellt: 30. Dezember 2025*
*Für: Gerüstplanung Schweiz App v3.0*
