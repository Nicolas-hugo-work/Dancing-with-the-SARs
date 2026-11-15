# CONTEXTO DEL PROYECTO: PACHAMETRICS (Dancing with the SARs - Cochabamba)

## 1. Visión y Diferenciador (El "Pitch")

- **PachaMetrics:** "Midiendo el espacio y el tiempo para proteger nuestra tierra". Plataforma cívica demostrativa de monitoreo.
- **El Valor:** Transformamos datos complejos de radar SAR (satélite NISAR, humedad milimétrica del suelo) y SENAMHI en un "Panel de Inteligencia Urbana y Prevención" para el Gobierno Autónomo Municipal de Cochabamba (GAMC).
- **Impacto Social:** Permite la toma de decisiones preventivas de presupuesto e ingeniería en los 15 distritos, especialmente en zonas vulnerables a hundimientos o inundaciones, salvando vidas y optimizando recursos municipales.

## 2. Estructura de la Plataforma (Flujo UI/UX)

1. **Landing/Exploración:** Introducción "¿Quiénes somos?" y acceso al Dashboard.
2. **Dashboard Principal:** Mapa Distrital interactivo con semaforización de riesgo (Bajo, Mod., Alto), selector rápido de distritos y panel de métricas actuales (Temperatura, Lluvia 24h, Humedad Suelo, Calidad Aire, Evolución Húmeda Radárica).
3. **Zonas de Interés:** Lista/Grid detallada de los 15 distritos con tarjetas que muestran estado de ladera, calidad de aire, nivel de río y riesgo específico[cite: 9].
4. **Historial Climático:** Línea de tiempo interactiva (2022, 2023, Actual 2024, Escenarios Futuros +2 años) con métricas comparativas y curvas estacionales[cite: 10].
5. **Centro de Alertas:** Mapa de focos de riesgo georreferenciados y tarjetas detalladas de "Riesgo de Anegamiento" o "Estabilidad de Laderas"[cite: 11].

## 3. Stack Tecnológico

- Backend: Django.
- Frontend: Next.js (App Router), TypeScript, Tailwind CSS, React-Leaflet (Mapas), GSAP (Animaciones).
