import type { Metadata } from "next";
import { Inter, Manrope } from "next/font/google";
import { AppProviders } from "@/app/providers";
import { SkipLink } from "@/components/atoms/skip-link";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });
const manrope = Manrope({ subsets: ["latin"], variable: "--font-manrope" });

export const metadata: Metadata = {
  title: "MedDiag Clinical Platform",
  description: "Clinical Atrium diagnostic workspace",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es">
      <body className={`${inter.variable} ${manrope.variable} font-body`}>
        <SkipLink />
        <AppProviders>{children}</AppProviders>
      </body>
    </html>
  );
}
