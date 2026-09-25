import type { Metadata } from "next";
import { JetBrains_Mono, Space_Grotesk } from "next/font/google";
import "./globals.css";

const spaceGrotesk = Space_Grotesk({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});


const jetbrainsMono = JetBrains_Mono({

  subsets: ["latin"],

  variable: "--font-mono",

  display: "swap",

});



export const metadata: Metadata = {

  title: "ModelDoctor — The MRI for your ML Pipeline",

  description:

    "AI-powered diagnostic system that catches silent failures in ML code before they reach production. By Team ASTROID.",

};



export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`${spaceGrotesk.variable} ${jetbrainsMono.variable}`}>
      <body className="font-sans antialiased">{children}</body>
    </html>
  );
}
