import type { Metadata } from "next";
import "./globals.css";
export const metadata: Metadata = {
  title: "PNSI | Health intelligence workspace",
  description:
    "Evidence-led monitoring and human-reviewed public health communication.",
};
export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fr">
      <body>{children}</body>
    </html>
  );
}
