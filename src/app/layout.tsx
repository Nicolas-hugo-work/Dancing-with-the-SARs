import type { Metadata, Viewport } from "next";
import { Nunito_Sans, Righteous } from "next/font/google";

import "leaflet/dist/leaflet.css";
import "./globals.css";

const nunitoSans = Nunito_Sans({
  subsets: ["latin"],
  variable: "--font-nunito-sans",
  display: "swap",
});

const righteous = Righteous({
  subsets: ["latin"],
  weight: "400",
  variable: "--font-righteous",
  display: "swap",
});

export const metadata: Metadata = {
  title: {
    default: "PachaMetrics · Inteligencia territorial de Cochabamba",
    template: "%s · PachaMetrics",
  },
  description:
    "Terminal de inteligencia geoespacial para la toma de decisiones en los distritos de Cochabamba.",
};

export const viewport: Viewport = {
  themeColor: "#184C32",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="es"
      className={`${nunitoSans.variable} ${righteous.variable}`}
    >
      <body className="h-full bg-cream font-sans text-pacha-700 antialiased">
        {children}
      </body>
    </html>
  );
}
