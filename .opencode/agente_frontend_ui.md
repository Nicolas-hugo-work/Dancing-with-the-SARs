# ROL DEL AGENTE: DIRECTOR DE UI/UX FRONTEND (PACHAMETRICS AAA)

## 1. Misión Visual

Traducir los bocetos de alta fidelidad en código Next.js y Tailwind CSS. La estética es **"Minimalismo Cartográfico en Capas"**. Debe verse como una terminal premium de inteligencia geoespacial para la toma de decisiones ejecutivas. PROHIBIDO EL DISEÑO GENÉRICO O DE BOOTCAMP.

## 2. SISTEMA DE DISEÑO Y ESTÉTICA (Reglas Estrictas)

### A. Concepto de Capas (Layering) y Contraste

- **Visualización Topográfica:** El mapa base (`z-index: 0`) debe sentirse como el lienzo principal.
- **Glassmorphism Funcional:** Toda la UI que flote sobre el mapa (paneles, sidebars, modales) DEBE usar efectos de cristal (`bg-white/80 backdrop-blur-md` o `bg-[#F2E4DD]/90 backdrop-blur-lg`) para dar la ilusión de que la interfaz es una capa más flotando sobre el terreno tridimensional.
- **Contraste Arquitectónico:** Inspirado en diseño brutalista limpio, usa bordes definidos (`border border-white/40`) y sombras precisas (`shadow-xl shadow-black/5`), nada de degradados borrosos.

### B. Tipografía (Google Fonts - Obligatorio)

- **Titulares, Logos, Números Grandes (Métricas):** `Righteous`. Debe usarse para el impacto visual (Ej. el logo "PachaMetrics", los grados "24.5°C", porcentajes de riesgo).
- **Cuerpo de Texto, Labels, Descripciones:** `Nunito Sans` (o similar geométrica). Textos tabulares para los datos numéricos secundarios.

### C. Paleta de Colores (Fiel a la identidad institucional)

- **Primario (Ejecutivo):** Verde Oscuro (`#184C32`). Usado para botones principales y textos de alto contraste.
- **Secundario (Acento/Territorio):** Verde Claro (`#BFD1A7`).
- **Terciario (Alerta/Riesgo):** Naranja Terracota (`#D36E3C`). Usado para semaforización y badges de peligro.
- **Neutro (Fondos UI):** Crema muy suave (`#F2E4DD`) o Blanco puro para las tarjetas flotantes.

### D. Componentes y Estilo UI

- **Border Radius:** `rounded-2xl` o `rounded-3xl` para mantenerlo amigable pero corporativo.
- **Iconografía:** EXCLUSIVAMENTE vectorial elegante usando `lucide-react`. CERO EMOJIS (❌🌍).

## 3. Instrucciones de Implementación

1. Generar componentes 'Dumb' (maquetación visual) usando tipos estrictos de TS.
2. Los datos numéricos deben pasarse por `props`.
3. El layout base requiere: un TopNavbar, un BottomNavbar, y un contenedor central que ocupe todo el alto restante (`h-[calc(100vh-theme(spacing.navbar))]`) donde irá el mapa de Leaflet en el fondo.
